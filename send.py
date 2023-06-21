import pika

from utils import get_configuration

STATE_EXCHANGE = 'state_change'
NOTIFICATION_EXCHANGE = 'state_notification'

configuration: dict[str, str | dict[str, str | dict]] = get_configuration()


def post_state_change(new_state: str, routing_key: str):
    send_message(new_state, routing_key, STATE_EXCHANGE)


def post_state_notification(current_state: str, routing_key: str, sender_id: str):
    send_message(sender_id + ":" + current_state, routing_key, NOTIFICATION_EXCHANGE)


def send_message(message: str, routing_key: str, exchange_name: str):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=configuration['URL']['address']))
    channel = connection.channel()

    channel.exchange_declare(exchange=('%s' % exchange_name), exchange_type='topic')

    channel.basic_publish(
        exchange=exchange_name, routing_key=routing_key, body=str.encode(message))
    # debug
    print(" [x] Sent %r:%r" % (routing_key, message))
    connection.close()
