import pika

import utils

STATE_EXCHANGE = 'state_change'
NOTIFICATION_EXCHANGE = 'state_notification'

configuration: dict[str, str | dict[str, str | dict]] = utils.get_configuration()


def post_state_change(new_state: str, routing_key: str) -> None:
    """
    Send new state to the children node

    :param new_state: new state
    :param routing_key: binding key of nodes that should receive the new state
    :return: None
    """
    send_message(new_state, routing_key, STATE_EXCHANGE)


def post_state_notification(current_state: str, routing_key: str, sender_id: str) -> None:
    """
    Update parent about current state

    :param current_state: node's current state
    :param routing_key: parent_id
    :param sender_id: node's id (binding key)
    :return: None
    """
    send_message(sender_id + ":" + current_state, routing_key, NOTIFICATION_EXCHANGE)


def send_message(message: str, routing_key: str, exchange_name: str) -> None:
    """
    Transfer message to the destination node's queue using exchange and routing key

    :param message: content
    :param routing_key: receiver queue id
    :param exchange_name:
    :return: None
    """
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=configuration['URL']['address']))
    channel = connection.channel()

    channel.exchange_declare(exchange=('%s' % exchange_name), exchange_type='topic')

    channel.basic_publish(exchange=exchange_name, routing_key=routing_key, body=str.encode(message))
    if configuration['debug'] == 'True':
        print(" [x] Sent message: %r -> %r" % (message, routing_key))
    connection.close()
