import asyncio
import json
import time

import model
import receive
import utils
from model import Node, NodeAddress, State

import pytest

pytest_plugins = ('pytest_asyncio',)
configuration: dict[str, str | dict[str, str | dict]] = utils.get_configuration()


class TestNode:
    def test_rpc_client_value(self):
        """
        Test all return values from that rpc_server responded
        :return:
        """
        init_node = generate_node(State.Initialisation)
        white_envelope = utils.get_white_envelope('get_state')
        chanel = ChannelStub()
        init_node.on_request(ch=chanel, body=white_envelope, method=MethodStub(), props=PropertiesStub())
        response = utils.get_dict_from_envelope(chanel.blue_msg)
        assert response['state'] == 'Initialisation' and len(response) == 1
        assert chanel.routing_key == 'reply_to'
        assert chanel.properties.correlation_id == 'correlation_id'

    def test_rpc_client_duration(self):
        """
        Test that rpc_server is responding in expected time (wait x seconds)
        :return:
        """
        init_node = generate_node(State.Initialisation)
        white_envelope = utils.get_white_envelope('get_state')
        chanel = ChannelStub()
        start = time.time()
        init_node.on_request(ch=chanel, body=white_envelope, method=MethodStub(), props=PropertiesStub())
        end = time.time()
        duration = end - start
        starting_time = configuration['node']['time']['get']
        assert starting_time - 1 < duration < starting_time + 1

    @pytest.mark.asyncio
    async def test_notify_message_one_parent(self):
        """
        Test notification propagation behaviour and updating own state
        Note: it does not test whether the message to parent is sent correctly
        :return:
        """
        raw_state = str(State.Error).split(':')[-1]
        receive.node = generate_node(State.Running, children={model.NodeAddress('127.0.0.1:sender'): []},
                                     address='127.0.0.1:22000')
        receive.loop = asyncio.get_event_loop()
        receive.callback(_ch=None, method=MethodStub(), _properties=None,
                         body=utils.get_red_envelope(raw_state, 'sender'))
        assert receive.node.state == State.Running
        await asyncio.sleep(1)
        assert receive.node.state == State.Error

        loop_stop()

    @pytest.mark.asyncio
    async def test_notify_message_node_already_error(self):
        """
        Test if notification influence node that is already in error state
        Note: it does not test whether the message to parent is sent correctly
        :return:
        """
        raw_state = str(State.Running).split(':')[-1]
        receive.node = generate_node(State.Error, children={model.NodeAddress('127.0.0.1:sender'): []})
        receive.loop = asyncio.get_event_loop()
        receive.callback(_ch=None, method=MethodStub(), _properties=None,
                         body=utils.get_red_envelope(raw_state, 'sender'))
        assert receive.node.state == State.Error
        await asyncio.sleep(1)
        assert receive.node.state == State.Error

        loop_stop()

    @pytest.mark.asyncio
    async def test_notify_message_one_child(self):
        """
        Test notification processing from one child.
        :return:
        """
        init_states = [State.Stopped, State.Running]
        for i in range(2):
            raw_state = str(init_states[i - 1]).split(':')[-1]
            receive.node = generate_node(init_states[1 - i], children={model.NodeAddress('127.0.0.1:sender'): []})
            receive.loop = asyncio.get_event_loop()
            receive.callback(_ch=None, method=MethodStub(), _properties=None,
                             body=utils.get_red_envelope(raw_state, 'sender'))
            assert receive.node.state == init_states[1 - i]
            await asyncio.sleep(1)
            assert receive.node.state == init_states[i - 1]

            loop_stop()

    @pytest.mark.asyncio
    async def test_notify_message_two_children(self):
        """
        Test notification processing from more children
        :return:
        """

        receive.node = generate_node(State.Stopped, children={model.NodeAddress('127.0.0.1:child_1'): [],
                                                              model.NodeAddress('127.0.0.1:child_2'): []})
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

        loop_stop()

    @pytest.mark.asyncio
    async def test_change_state_message_no_child_running(self):
        """
        Test changing state Stopped->Running behaviour after receiving the command without propagation to children
        :return:
        """
        raw_state = str(State.Running).split('.')[-1]

        receive.node = generate_node(State.Stopped)
        receive.loop = asyncio.get_event_loop()
        receive.callback(_ch=None, method=MethodStub(), _properties=None,
                         body=utils.get_orange_envelope(raw_state))
        assert receive.node.state == State.Stopped
        await asyncio.sleep(1)
        assert receive.node.state == State.Starting
        await asyncio.sleep(configuration['node']['time']['starting'])
        assert receive.node.state == State.Running

        loop_stop()

    @pytest.mark.asyncio
    async def test_change_state_message_no_child_error(self):
        """
        Test changing state Error->Stopped behaviour after receiving the command without propagation to children
        :return:
        """
        raw_state = str(State.Stopped).split('.')[-1]

        receive.node = generate_node(State.Error)
        receive.loop = asyncio.get_event_loop()
        receive.callback(_ch=None, method=MethodStub(), _properties=None,
                         body=utils.get_orange_envelope(raw_state))
        assert receive.node.state == State.Error
        await asyncio.sleep(1)
        assert receive.node.state == State.Error

        loop_stop()

    @pytest.mark.asyncio
    async def test_change_state_message_no_child_stopped(self):
        """
        Test changing state Running->Stopped behaviour after receiving the command without propagation to children
        :return:
        """
        raw_state = str(State.Stopped).split('.')[-1]

        receive.node = generate_node(State.Running)
        receive.loop = asyncio.get_event_loop()
        receive.callback(_ch=None, method=MethodStub(), _properties=None,
                         body=utils.get_orange_envelope(raw_state))
        assert receive.node.state == State.Running
        await asyncio.sleep(1)
        assert receive.node.state == State.Stopped

        loop_stop()

    @pytest.mark.asyncio
    async def test_change_state_message_two_children(self):
        """
        Test changing state and waiting to children notification in order to change the state
        :return:
        """
        raw_state = str(State.Running).split('.')[-1]

        receive.node = generate_node(State.Stopped)
        receive.node.children = {model.NodeAddress('127.0.0.1:child_1'): [], model.NodeAddress('127.0.0.1:child_2'): []}
        receive.loop = asyncio.get_event_loop()
        receive.callback(_ch=None, method=MethodStub(), _properties=None,
                         body=utils.get_orange_envelope(raw_state))
        assert receive.node.state == State.Stopped
        await asyncio.sleep(1)
        assert receive.node.state == State.Starting
        await asyncio.sleep(configuration['node']['time']['starting'])
        assert receive.node.state == State.Starting  # node won't change the state before its child

        receive.callback(_ch=None, method=MethodStub(), _properties=None,
                         body=utils.get_red_envelope('Running', 'child_2'))
        await asyncio.sleep(1)
        assert receive.node.state == State.Initialisation  # one child Running one no notification -> Initialisation
        receive.callback(_ch=None, method=MethodStub(), _properties=None,
                         body=utils.get_red_envelope('Running', 'child_1'))
        await asyncio.sleep(configuration['node']['time']['starting'])
        assert receive.node.state == State.Running

        loop_stop()


def generate_node(state: State, address: str = '127.0.0.0:20000', children: dict[NodeAddress, [State]] = None) -> Node:
    node_add = NodeAddress(address)
    node = Node(node_add)
    node.state = state
    if children:
        node.children = children
    return node


def loop_stop():
    for task in sorted(list(asyncio.all_tasks()), key=lambda x: int(x.get_name().split('-')[-1]))[1:]:
        task.cancel()


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


@pytest.fixture(scope="session", autouse=True)
def do_something(request):
    original_architecture = utils.set_architecture('MOM')
    request.addfinalizer(lambda: utils.set_architecture(original_architecture))
