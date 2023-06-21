import asyncio
import signal
import time
from datetime import datetime

import pika

import model
import send
from model import Node
from utils import get_configuration, get_bounding_key, get_port

STATE_EXCHANGE = 'state_change'
NOTIFICATION_EXCHANGE = 'state_notification'

configuration: dict[str, str | dict[str, str | dict]] = get_configuration()
node: Node | None = None


def initialised() -> None:
    """
    Method executed when API is fully initialized, notify its parent about being redy

    :return: None
    """
    if not node.children:
        node.state = model.State.Stopped
    send.post_state_notification(current_state=str(node.state),
                                 routing_key=get_bounding_key(node.get_parent().get_port()),
                                 sender_id=get_bounding_key(node.address.get_port()))


async def shutdown_event() -> None:
    """
    Send SIGTERM to all children before termination and wait up 20s for child termination if not set other limit

    :return: None
    """
    if node:
        sleeping_time = 0
        max_sleep = configuration['node']['time']['shutdown']
        for process in node.started_processes:
            process.send_signal(signal.SIGTERM)
        for process in node.started_processes:
            sleeping_time = 0
            while process.poll is None and sleeping_time < max_sleep:
                await asyncio.sleep(1)
                sleeping_time += 1
        if sleeping_time < max_sleep:
            print('No running child processes')
        else:
            print('Child process might still run!')
        print(node.address.get_full_address() + ' is going to be terminated!')
    await asyncio.sleep(1)  # only to see termination messages from children in IDE


def get_state() -> dict[str, str]:
    time.sleep(configuration['node']['time']['get'])
    return {"State": str(node.state)}


async def change_state(start: str = None, stop: str = None, debug: bool = False) -> model.State:
    """
    Endpoint to change node state.

    :param start: probability between 0 and 1 of getting into Error state
    :param stop: any non None input means stop
    :param debug: prints debug messages for each node (when started and when did transition)
    :return: node state after transition
    """
    if debug:
        now = datetime.now()
        print("Node " + node.address.get_port() + " received POST " + now.strftime(" %H:%M:%S"))
    if node.state == model.State.Error:
        return node.state
    if start and node.state == model.State.Stopped:
        node.state = model.State.Starting
        asyncio.create_task(node.set_state(model.State.Running, float(start), debug,
                                           configuration['node']['time']['starting']))
    elif stop and node.state == model.State.Running:
        asyncio.create_task(node.set_state(model.State.Stopped, debug=debug,
                                           transition_time=configuration['node']['time']['starting']))
    else:
        # raise HTTPException(status_code=400, detail="Combination of current state and transition state is not allowed!")
        pass
    return node.state


def notify(state: str = None, sender_port: str = None) -> None:
    """
    Child current state notification that is recursively propagating to the root and updating states on the way

    :param state: state of the child that sent notification
    :param sender_port: child's address
    :return: None
    """
    full_address = configuration['URL']['address'] + ':' + sender_port
    if state:
        node.children[model.NodeAddress(full_address)].append(model.State[state.split('.')[-1]])
        node.update_state()
    if node.get_parent().address is None:
        return
    send.post_state_notification(current_state=str(node.state),
                                 routing_key=get_bounding_key(node.get_parent().get_port()),
                                 sender_id=get_bounding_key(node.address.get_port()))


def run(created_node: Node):
    global node
    node = created_node
    binding_key = get_bounding_key(node.address.get_port())
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=configuration['URL']['address']))
    channel = connection.channel()

    channel.exchange_declare(exchange=STATE_EXCHANGE, exchange_type='topic')
    channel.exchange_declare(exchange=NOTIFICATION_EXCHANGE, exchange_type='topic')

    result = channel.queue_declare('', exclusive=True)
    queue_name = result.method.queue

    channel.queue_bind(exchange=STATE_EXCHANGE, queue=queue_name, routing_key=binding_key)
    channel.queue_bind(exchange=NOTIFICATION_EXCHANGE, queue=queue_name, routing_key=binding_key)

    initialised()
    print(binding_key + ' - initialized')

    def callback(ch, method, properties, body):
        message = body.decode("utf-8")
        if ':' in message:
            sender_id = get_port(message.split(':')[0])
            current_state = message.split(':')[1]
            notify(current_state, sender_id)
        else:
            change_state(start=None, stop=None, debug=True)
        print(" [x] %r:%r" % (method.routing_key, body))

    channel.basic_consume(
        queue=queue_name, on_message_callback=callback, auto_ack=True)

    channel.start_consuming()
