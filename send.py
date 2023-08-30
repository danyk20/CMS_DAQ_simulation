import asyncio

import aioamqp

import utils

STATE_EXCHANGE = 'state_change'
NOTIFICATION_EXCHANGE = 'state_notification'

configuration: dict[str, str | dict[str, str | dict]] = utils.get_configuration()

channel = None
transport = None
protocol = None


async def open_chanel() -> None:
    global channel, transport, protocol
    try:
        transport, protocol = await aioamqp.connect(host=configuration['URL']['address'], port=5672, login='guest',
                                                    password='guest')
    except aioamqp.AmqpClosedConnection:
        print('Connection is closed!')
    channel = await protocol.channel()
    if configuration['debug']:
        print('Channel created!')


async def close_channel() -> None:
    """
    Closed opened and unused resources

    :return: None
    """
    if protocol:
        try:
            await protocol.close(timeout=1)
        except asyncio.exceptions.TimeoutError:
            if configuration['debug']:
                print('Connection still in use!')
    if transport:
        transport.close()


async def push_message(exchange_name, routing_key, message) -> None:
    """
    Push message to the broker asynchronously

    :param exchange_name: exchange name
    :param routing_key: recipient queue id
    :param message: string message
    :return: None
    """
    if not channel:
        await open_chanel()

    try:
        await channel.basic_publish(
            payload=message.encode('utf-8'),
            exchange_name=exchange_name,
            routing_key=routing_key
        )
    except Exception as e:
        if configuration['debug']:
            print(str(e))
            print('message: ' + str(message))

    if configuration['debug']:
        print(" [x] Sent message: %r -> %r" % (message, routing_key))


async def post_state_change(new_state: str, routing_key: str, chance_to_fail: float = 0) -> None:
    """
    Send new state to the children node

    :param chance_to_fail: probability to end in Error state
    :param new_state: new state
    :param routing_key: binding key of nodes that should receive the new state
    :return: None
    """
    raw_state = new_state.split('.')[-1]
    await send_message(utils.get_orange_envelope(raw_state, chance_to_fail), routing_key, STATE_EXCHANGE)


async def post_state_notification(current_state: str, routing_key: str, sender_id: str) -> None:
    """
    Update parent about current state

    :param current_state: node's current state
    :param routing_key: parent_id
    :param sender_id: node's id (binding key)
    :return: None
    """
    raw_state = current_state.split('.')[-1]
    await send_message(utils.get_red_envelope(raw_state, sender_id), routing_key, NOTIFICATION_EXCHANGE)


async def send_message(message: str | bytes, routing_key: str, exchange_name: str) -> None:
    """
    Transfer message to the destination node's queue using exchange and routing key

    :param message: content
    :param routing_key: receiver queue id
    :param exchange_name:
    :return: None
    """
    if routing_key:
        try:
            await push_message(exchange_name, routing_key, message)
        except Exception as e:
            print(e)
    else:
        if configuration['debug']:
            print('No routing key - discarding: ' + str(message))
