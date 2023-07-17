import json

import utils
from model import Node, NodeAddress, State

import pytest


def generate_node(state: State, address: str = '127.0.0.0:20000', ) -> Node:
    node_add = NodeAddress(address)
    node = Node(node_add)
    node.state = state
    return node


class ChannelStub:

    def __init__(self):
        self.blue_msg = ''

    def basic_publish(self, exchange, routing_key, properties, body):
        self.blue_msg = body

    def basic_ack(self, delivery_tag):
        pass


class MethodStub:

    def __init__(self):
        self.delivery_tag = 'delivery_tag'


class PropertiesStub:

    def __init__(self):
        self.reply_to = 'reply_to'
        self.correlation_id = 'correlation_id'


def test_rpc_client_value():
    init_node = generate_node(State.Initialisation)
    white_envelope = utils.get_white_envelope('get_state')
    chanel = ChannelStub()
    init_node.on_request(ch=chanel, body=white_envelope, method=MethodStub(), props=PropertiesStub())
    response = json.loads(chanel.blue_msg)
    assert response == '{"state": "Initialisation"}'
