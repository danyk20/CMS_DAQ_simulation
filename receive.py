import pika

from model import Node
from utils import get_configuration, get_bounding_key

STATE_EXCHANGE = 'state_change'
NOTIFICATION_EXCHANGE = 'state_notification'

configuration: dict[str, str | dict[str, str | dict]] = get_configuration()
node: Node | None = None


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

    print(binding_key + ' - initialized')

    def callback(ch, method, properties, body):
        print(" [x] %r:%r" % (method.routing_key, body))

    channel.basic_consume(
        queue=queue_name, on_message_callback=callback, auto_ack=True)

    channel.start_consuming()
