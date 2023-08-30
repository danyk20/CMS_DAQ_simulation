import asyncio
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
loop: AbstractEventLoop | None = None


def initialised() -> None:
    """
    Method executed when API is fully initialized, notify its parent about being redy

    :return: None
    """
    if not node.children:
        node.state = model.State.Stopped
    asyncio.new_event_loop().run_until_complete(send.post_state_notification(current_state=str(node.state),
                                                                             routing_key=utils.get_bounding_key(
                                                                                 node.get_parent().get_port()),
                                                                             sender_id=utils.get_bounding_key(
                                                                                 node.address.get_port())))


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
    if configuration['debug']:
        now = datetime.now()
        print("Node " + node.address.get_port() + " received " + new_state + " at " + now.strftime(" %H:%M:%S"))
    if node.state == model.State.Error:
        return
    if start and node.state == model.State.Stopped:
        node.state = model.State.Starting
        for child_port in node.children:
            node.children[child_port] = (model.State.Starting, node.children[child_port][1])
        asyncio.create_task(node.set_state(model.State.Running, float(start),
                                           transition_time=configuration['node']['time']['starting']))
    elif stop and node.state == model.State.Running:
        asyncio.create_task(
            node.set_state(model.State.Stopped, transition_time=configuration['node']['time']['starting']))
    elif configuration['debug']:
        print('Wrong operation! Node remains in : %r' % str(node.state))


async def notify(state: str = None, sender_port: int = None, time_stamp: float = 0) -> None:
    """
    Child current state notification that is recursively propagating to the root and updating states on the way

    :param state: state of the child that sent notification
    :param sender_port: child's address
    :param time_stamp: when was notification issued
    :return: None
    """
    state_changed = False
    if state and node.children[sender_port][1] < time_stamp:
        try:
            node.children[sender_port] = (model.State[state.split('.')[-1]], time_stamp)
            state_changed = node.update_state()
        except KeyError:
            if configuration['debug']:
                print('Invalid notification! Node remains in : %r' % str(node.state))

    if node.get_parent().address is None:
        return
    if state_changed:
        await send.post_state_notification(current_state=str(node.state),
                                           routing_key=utils.get_bounding_key(node.get_parent().get_port()),
                                           sender_id=utils.get_bounding_key(node.address.get_port()))


def callback(_ch, method, _properties, body):
    message = utils.exception_filter(lambda: utils.get_dict_from_envelope(body, ['orange', 'red']))
    if not message:
        return
    if message['type'] == 'Notification':
        # notification
        sender_id = utils.get_port(message['sender'])
        current_state = message['toState']
        time_stamp = message['time_stamp']
        asyncio.run_coroutine_threadsafe(notify(current_state, int(sender_id), time_stamp), loop)
    elif message['type'] == 'Input':
        # change state
        start_state = None
        stop_state = None
        if message['name'] == 'Running':
            start_state = str(message['parameters']['chance_to_fail'])
        elif message['name'] == 'Stopped':
            stop_state = True
        asyncio.run_coroutine_threadsafe(change_state(start=start_state, stop=stop_state), loop)
    if configuration['debug']:
        print("Node %r received message: %r" % (method.routing_key, message))


def run(created_node: model.Node, async_loop: AbstractEventLoop) -> None:
    """
    Run rabbitmq consumer -> proces all messages received in queue

    :param created_node: related node
    :param async_loop: infinite loop
    :return: None
    """
    global node, loop
    loop = async_loop
    node = created_node
    binding_key = utils.get_bounding_key(node.address.get_port())
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=configuration['URL']['address']))
    channel = connection.channel()

    channel.exchange_declare(exchange=STATE_EXCHANGE, exchange_type='topic')
    channel.exchange_declare(exchange=NOTIFICATION_EXCHANGE, exchange_type='topic')

    queue_name = 'topic_queue:' + utils.get_bounding_key(node.address.get_port())
    result = channel.queue_declare(queue_name, exclusive=True)
    queue_name = result.method.queue

    channel.queue_bind(exchange=STATE_EXCHANGE, queue=queue_name, routing_key=binding_key)
    channel.queue_bind(exchange=NOTIFICATION_EXCHANGE, queue=queue_name, routing_key=binding_key)

    initialised()
    if configuration['debug']:
        print(binding_key + ' - initialized')

    def stop():
        """Stop listening for jobs"""
        connection.add_callback_threadsafe(_stop)

    def _stop():
        try:
            channel.stop_consuming()
        except Exception as e:
            print('Channel cannot stop consuming on node:' + node.address.get_port() + str(e))
        try:
            channel.close()
        except Exception as e:
            print('Channel cannot be closed on node:' + node.address.get_port() + str(e))
        try:
            connection.close()
        except Exception as e:
            print('Connection cannot be closed on node:' + node.address.get_port() + str(e))

    node.kill_consumer = stop

    channel.basic_consume(
        queue=queue_name, on_message_callback=callback, auto_ack=True)

    node.channel_tag = queue_name
    node.channel = channel
    channel.start_consuming()
