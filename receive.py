import asyncio
import json
import time
from asyncio import AbstractEventLoop
from datetime import datetime

import pika

import model
import send
import utils

STATE_EXCHANGE = 'state_change'
NOTIFICATION_EXCHANGE = 'state_notification'

configuration: dict[str, str | dict[str, str | dict]] = utils.get_configuration()
node: model.Node | None = None
loop = None


def initialised() -> None:
    """
    Method executed when API is fully initialized, notify its parent about being redy

    :return: None
    """
    if not node.children:
        node.state = model.State.Stopped
    send.post_state_notification(current_state=str(node.state),
                                 routing_key=utils.get_bounding_key(node.get_parent().get_port()),
                                 sender_id=utils.get_bounding_key(node.address.get_port()))


def get_state() -> dict[str, str]:
    time.sleep(configuration['node']['time']['get'])
    return {"State": str(node.state)}


async def change_state(start: str = None, stop: str = None) -> None:
    """
    Endpoint to change node state.

    :param start: probability between 0 and 1 of getting into Error state
    :param stop: any non None input means stop
    :return: None
    """
    new_state = 'State.Running' if start else 'State.Stopped'
    if configuration['debug'] == 'True':
        now = datetime.now()
        print("Node " + node.address.get_port() + " received " + new_state + " at " + now.strftime(" %H:%M:%S"))
    if node.state == model.State.Error:
        return
    if start and node.state == model.State.Stopped:
        node.state = model.State.Starting
        asyncio.create_task(node.set_state(model.State.Running, float(start),
                                           transition_time=configuration['node']['time']['starting']))
    elif stop and node.state == model.State.Running:
        asyncio.create_task(
            node.set_state(model.State.Stopped, transition_time=configuration['node']['time']['starting']))
    elif configuration['debug'] == 'True':
        print('Wrong operation! %r -> %r' % (node.state, new_state))
    # asyncio.get_running_loop() no problem


async def notify(state: str = None, sender_port: str = None) -> None:
    """
    Child current state notification that is recursively propagating to the root and updating states on the way

    :param state: state of the child that sent notification
    :param sender_port: child's address
    :return: None
    """
    full_address = configuration['URL']['address'] + ':' + sender_port
    if state:
        node.children[model.NodeAddress(full_address)].append(model.State[state.split('.')[-1]])
        # asyncio.get_running_loop() exception
        node.update_state()
    if node.get_parent().address is None:
        return
    send.post_state_notification(current_state=str(node.state),
                                 routing_key=utils.get_bounding_key(node.get_parent().get_port()),
                                 sender_id=utils.get_bounding_key(node.address.get_port()))


def run(created_node: model.Node, async_loop: AbstractEventLoop) -> None:
    """
    Run rabbitmq consumer -> proces all messages received in queue

    :param created_node: related node
    :param async_loop: infinite loop
    :return: None
    """
    global node
    node = created_node
    binding_key = utils.get_bounding_key(node.address.get_port())
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=configuration['URL']['address']))
    channel = connection.channel()

    channel.exchange_declare(exchange=STATE_EXCHANGE, exchange_type='topic')
    channel.exchange_declare(exchange=NOTIFICATION_EXCHANGE, exchange_type='topic')

    queue_name = 'consumer:' + utils.get_bounding_key(node.address.get_port())
    result = channel.queue_declare(queue_name, exclusive=True)
    queue_name = result.method.queue

    channel.queue_bind(exchange=STATE_EXCHANGE, queue=queue_name, routing_key=binding_key)
    channel.queue_bind(exchange=NOTIFICATION_EXCHANGE, queue=queue_name, routing_key=binding_key)

    initialised()
    print(binding_key + ' - initialized')

    def callback(_ch, method, _properties, body):
        message = json.loads(body)
        if message['type'] == 'Notification':
            # notification
            sender_id = utils.get_port(message['sender'])
            current_state = message['toState']
            asyncio.run_coroutine_threadsafe(notify(current_state, sender_id), async_loop)
        elif message['type'] == 'Input':
            # change state
            start_state = None
            stop_state = None
            if message['name'] == 'Running':
                start_state = str(message['parameters']['chance_to_fail'])
            elif message == 'State.Stopped':
                stop_state = True

            asyncio.run_coroutine_threadsafe(change_state(start=start_state, stop=stop_state), async_loop)
        print("Node %r received message: %r" % (method.routing_key, message))

    def stop():
        """Stop listening for jobs"""
        connection.add_callback_threadsafe(_stop)

    def _stop():
        channel.stop_consuming()
        channel.close()
        connection.close()

    node.kill_consumer = stop

    channel.basic_consume(
        queue=queue_name, on_message_callback=callback, auto_ack=True)

    node.channel_tag = queue_name
    node.channel = channel
    channel.start_consuming()
