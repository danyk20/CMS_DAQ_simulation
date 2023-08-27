import asyncio
import threading

import pika

import utils

STATE_EXCHANGE = 'state_change'
NOTIFICATION_EXCHANGE = 'state_notification'

configuration: dict[str, str | dict[str, str | dict]] = utils.get_configuration()

channel = None
connection = None


def open_chanel():
    global channel, connection
    if not channel:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=configuration['URL']['address']))
        channel = connection.channel()


def close_connection():
    global connection
    connection.close()


def post_state_change(new_state: str, routing_key: str, chance_to_fail: float = 0) -> None:
    """
    Send new state to the children node

    :param chance_to_fail: probability to end in Error state
    :param new_state: new state
    :param routing_key: binding key of nodes that should receive the new state
    :return: None
    """
    raw_state = new_state.split('.')[-1]
    threading.Thread(
        send_message(utils.get_orange_envelope(raw_state, chance_to_fail), routing_key, STATE_EXCHANGE)).start()


def post_state_notification(current_state: str, routing_key: str, sender_id: str) -> None:
    """
    Update parent about current state

    :param current_state: node's current state
    :param routing_key: parent_id
    :param sender_id: node's id (binding key)
    :return: None
    """
    raw_state = current_state.split('.')[-1]
    threading.Thread(
        target=send_message(utils.get_red_envelope(raw_state, sender_id), routing_key, NOTIFICATION_EXCHANGE)).start()


def send_message(message: str | bytes, routing_key: str, exchange_name: str) -> None:
    """
    Transfer message to the destination node's queue using exchange and routing key

    :param message: content
    :param routing_key: receiver queue id
    :param exchange_name:
    :return: None
    """
    global channel
    try:
        if routing_key:
            channel.exchange_declare(exchange=('%s' % exchange_name), exchange_type='topic')

            channel.basic_publish(exchange=exchange_name, routing_key=routing_key, body=message,
                                  properties=pika.BasicProperties(content_type='application/json'))
            if configuration['debug']:
                print(" [x] Sent message: %r -> %r" % (message, routing_key))

    except Exception as e:
        print(e)
