import sys

import pika
import uuid

from utils import get_configuration

NODE_ROUTING_KEY = sys.argv[1] if len(sys.argv) else '2.3.3.0.0'

configuration: dict[str, str | dict[str, str | dict]] = get_configuration()


class StateRpcClient(object):

    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=configuration['URL']['address']))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)

        self.response = None
        self.corr_id = None

    def on_response(self, _ch, _method, props, body):
        """
        Process received reply from rpc server

        :param _ch:
        :param _method:
        :param props:
        :param body:
        :return:
        """
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, routing_key) -> bin:
        """
        Sends get_state request to rpc server

        :param routing_key: rpc server ID
        :return: state of the node
        """
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='',
            routing_key='rpc_queue' + routing_key,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=b'get_state')
        self.connection.process_data_events(time_limit=int(configuration['rabbitmq']['rpc_timeout']))
        return self.response


get_state = StateRpcClient()

print(" [->] Requesting state from node " + NODE_ROUTING_KEY)
response = get_state.call(NODE_ROUTING_KEY)
print(" [<-] Received %r" % response.decode('utf-8'))
