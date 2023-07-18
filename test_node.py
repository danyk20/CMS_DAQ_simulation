import asyncio
import json
import time

import model
import receive
import utils
from model import Node, NodeAddress, State

import pytest

pytest_plugins = ('pytest_asyncio',)


class TestNode:
    def test_rpc_client_value(self):
        init_node = generate_node(State.Initialisation)
        white_envelope = utils.get_white_envelope('get_state')
        chanel = ChannelStub()
        init_node.on_request(ch=chanel, body=white_envelope, method=MethodStub(), props=PropertiesStub())
        response = json.loads(chanel.blue_msg)
        assert response == '{"state": "Initialisation"}'
        assert chanel.routing_key == 'reply_to'
        assert chanel.properties.correlation_id == 'correlation_id'

    def test_rpc_client_duration(self):
        init_node = generate_node(State.Initialisation)
        white_envelope = utils.get_white_envelope('get_state')
        chanel = ChannelStub()
        start = time.time()
        init_node.on_request(ch=chanel, body=white_envelope, method=MethodStub(), props=PropertiesStub())
        end = time.time()
        duration = end - start
        assert 9 < duration < 11

    @pytest.mark.asyncio
    async def test_notify_message_one_child(self):
        init_states = [State.Stopped, State.Running]
        for i in range(2):
            raw_state = str(init_states[i - 1]).split(':')[-1]
            receive.node = generate_node(init_states[1 - i])
            receive.node.children = {model.NodeAddress('127.0.0.1:sender'): []}
            receive.loop = asyncio.get_event_loop()
            receive.callback(_ch=None, method=MethodStub(), _properties=None,
                             body=utils.get_red_envelope(raw_state, 'sender'))
            assert receive.node.state == init_states[1 - i]
            await asyncio.sleep(1)
            assert receive.node.state == init_states[i - 1]

            for task in asyncio.all_tasks():
                if task.get_name() == 'Task-3':
                    task.cancel()

    @pytest.mark.asyncio
    async def test_notify_message_two_children(self):

        receive.node = generate_node(State.Stopped)
        receive.node.children = {model.NodeAddress('127.0.0.1:child_1'): [], model.NodeAddress('127.0.0.1:child_2'): []}
        receive.loop = asyncio.get_event_loop()
        receive.callback(_ch=None, method=MethodStub(), _properties=None,
                         body=utils.get_red_envelope('Starting', 'child_1'))
        assert receive.node.state == State.Stopped  # node created with this state
        await asyncio.sleep(1)
        assert receive.node.state == State.Initialisation  # default state when missing notification from any child
        receive.callback(_ch=None, method=MethodStub(), _properties=None,
                         body=utils.get_red_envelope('Stopped', 'child_2'))
        await asyncio.sleep(1)
        assert receive.node.state == State.Stopped  # one child Stopped one Starting -> Stopped
        receive.callback(_ch=None, method=MethodStub(), _properties=None,
                         body=utils.get_red_envelope('Running', 'child_2'))
        await asyncio.sleep(1)
        assert receive.node.state == State.Starting  # one child Running one Starting -> Starting
        receive.callback(_ch=None, method=MethodStub(), _properties=None,
                         body=utils.get_red_envelope('Running', 'child_1'))
        await asyncio.sleep(1)
        assert receive.node.state == State.Running  # all children Running
        receive.callback(_ch=None, method=MethodStub(), _properties=None,
                         body=utils.get_red_envelope('Error', 'child_1'))
        await asyncio.sleep(1)
        assert receive.node.state == State.Error  # at least one child in Error state

        for task in sorted(list(asyncio.all_tasks()), key=lambda x: x.get_name())[1:]:  # cancel all tasks except itself
            task.cancel()


def generate_node(state: State, address: str = '127.0.0.0:20000', ) -> Node:
    node_add = NodeAddress(address)
    node = Node(node_add)
    node.state = state
    return node


class ChannelStub:

    def __init__(self):
        self.blue_msg = ''
        self.routing_key = ''
        self.properties = None

    def basic_publish(self, exchange, routing_key, properties, body):
        self.blue_msg = body
        self.routing_key = routing_key
        self.properties = properties

    def basic_ack(self, delivery_tag):
        pass


class MethodStub:

    def __init__(self):
        self.delivery_tag = 'delivery_tag'
        self.routing_key = 'routing_key'


class PropertiesStub:

    def __init__(self):
        self.reply_to = 'reply_to'
        self.correlation_id = 'correlation_id'
