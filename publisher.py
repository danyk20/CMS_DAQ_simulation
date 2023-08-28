import asyncio
import aioamqp

import utils

configuration: dict[str, str | dict[str, str | dict]] = utils.get_configuration()


@asyncio.coroutine
def new_task(exchange_name, routing_key, message):
    try:
        transport, protocol = yield from aioamqp.connect(host='127.0.0.1', port=5672, login='guest', password='guest')
    except aioamqp.AmqpClosedConnection:
        print('Connection is closed! Message ' + str(message) + 'could not be sent!')

    channel = yield from protocol.channel()
    yield from channel.exchange_declare(exchange_name=exchange_name, type_name='topic')

    yield from channel.basic_publish(
        payload=message.encode('utf-8'),
        exchange_name=exchange_name,
        routing_key=routing_key,
        properties={
            'delivery_mode': 2
        }
    )
    yield from protocol.close()
    transport.close()
    if configuration['debug']:
        print(" [x] Sent message: %r -> %r" % (message, routing_key))
