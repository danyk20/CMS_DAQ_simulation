import asyncio
import socket

import aiohttp
import json
import os
import pytest
import signal
import subprocess
import time

from aiohttp import ClientConnectorError

import utils
from client import request_node

pytest_plugins = ('pytest_asyncio',)
configuration: dict[str, str | dict[str, str | dict | int]] = utils.get_configuration()

CHILDREN = '3'
LEVELS = '2'
PORT = '20000'


class TestNode:
    @pytest.mark.asyncio
    @pytest.mark.usefixtures('run_around_tests')
    async def test_get_value(self):
        """
        Test get request from all nodes
        :return: None
        """
        ports = list(get_all_ports())
        ports.sort()
        for port in ports:
            assert await get_state(port) == {"State": "State.Stopped"}

    @pytest.mark.asyncio
    @pytest.mark.usefixtures('run_around_tests')
    async def test_get_duration(self):
        """
        Test get request time duration
        :return: None
        """
        start = time.time()
        await get_state()
        end = time.time()
        duration = end - start
        starting_time = configuration['node']['time']['get']
        assert starting_time < duration < starting_time + 2

    @pytest.mark.parametrize('run_around_tests', [{'port': '20000', 'children': '3', 'levels': '0'}], indirect=True)
    @pytest.mark.asyncio
    async def test_single_node(self, run_around_tests):
        """
        Test single node Stopped->Running->Stopped->Error
        :param run_around_tests: function to set up environment for the test and clean afterward
        :return: None
        """
        start = {'start': '0'}
        stop = {'stop': '_'}
        error = {'start': '1'}

        assert await get_state() == {"State": "State.Stopped"}

        asyncio.get_running_loop().create_task(post_state(start))
        assert await get_state() == {"State": "State.Starting"}
        await asyncio.sleep(configuration['node']['time']['starting'])
        assert await get_state() == {"State": "State.Running"}

        await post_state(stop)
        assert await get_state() == {"State": "State.Stopped"}

        asyncio.get_running_loop().create_task(post_state(error))
        assert await get_state() == {"State": "State.Starting"}
        await asyncio.sleep(configuration['node']['time']['starting'])
        assert await get_state() == {"State": "State.Error"}

    @pytest.mark.asyncio
    @pytest.mark.usefixtures('run_around_tests')
    async def test_middle_node_interaction(self):
        """
        Complex test testing change state propagation to children and also notification propagation to the parent
        :return: None
        """
        params = {'start': '1'}
        # set the most left children of the root to error state
        error_initiator = sorted(list(get_children_ports(PORT)))[0]
        asyncio.get_running_loop().create_task(post_state(params, error_initiator))
        assert await get_state(error_initiator) == {"State": "State.Starting"}
        await asyncio.sleep(configuration['node']['time']['starting'])
        assert await get_state(error_initiator) == {"State": "State.Error"}
        # check that error was propagated to the parent
        assert await get_state() == {"State": "State.Error"}
        # check that all its children are in error state
        for port in get_children_ports(error_initiator):
            assert await get_state(port) == {"State": "State.Error"}
        # all other nodes are stopped
        stopped_nodes = (get_children_ports(PORT).difference({error_initiator})).difference(
            get_children_ports(error_initiator))
        for port in stopped_nodes:
            assert await get_state(port) == {"State": "State.Stopped"}


@pytest.fixture
def run_around_tests(request):
    port = PORT
    levels = LEVELS
    children = CHILDREN
    if 'param' in dir(request):
        port = request.param['port']
        levels = request.param['levels']
        children = request.param['children']
    path = os.path.join(os.getcwd(), '..')
    process = subprocess.Popen(["python", "service.py", '--port', port, '--levels', levels, '--children', children],
                               cwd=path)
    yield
    process.send_signal(signal.SIGTERM)
    for port in get_all_ports():
        if not is_terminated(port):  # ensure nodes are correctly terminated before the next test
            raise Exception('Cannot terminate node: ' + str(port))


@pytest.fixture(scope="session", autouse=True)
def configure_configuration_file(request) -> None:
    """
    Temporally change the configuration file in order to set the correct architecture

    :param request: request.addfinalizer is executed after all test are finished
    :return: None
    """
    os.chdir(os.path.dirname(__file__))
    original_architecture = utils.set_architecture('REST')
    request.addfinalizer(lambda: utils.set_architecture(original_architecture))


def get_children_ports(parent_port: str):
    """
    Get all children of the specific port

    :param parent_port: port number
    :return:
    """
    child_level = utils.compute_hierarchy_level(parent_port) + 1
    ports = set()
    for child in range(int(CHILDREN)):
        node_port = list(parent_port)
        node_port[child_level] = str(child + 1)
        ports.add(''.join(node_port))

    for port in ports:
        if child_level < int(LEVELS):
            ports = ports.union(get_children_ports(port))
    return ports


def get_all_ports():
    ports = get_children_ports(PORT)
    ports.add(PORT)
    return ports


async def get_state(port: str = PORT) -> str:
    counter = 0
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        configuration['URL']['protocol'] + configuration['URL']['address'] + ':' + port +
                        configuration['URL']['get_state']) as resp:
                    assert resp.status == 200
                    return json.loads(await resp.text())
        except ClientConnectorError:
            if counter:
                time.sleep(1)  # skip waiting for the first failure
            counter += 1
            if counter > configuration['REST']['timeout']:
                return ""


async def post_state(param: dict, port: str = PORT) -> None:
    url = configuration['URL']['address'] + ':' + port + configuration['URL']['change_state']
    await request_node(url, param)


def is_open(port):
    """
    Check whether the port is open or not

    :param port: numeric value of the port
    :return: boolean whether the port is open or not
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((configuration['URL']['address'], int(port)))
    return result == 0


def is_terminated(port):
    """
    Check whether the port is terminated or not and wait for termination up to Xs defined in configuration file

    :param port: numeric value of the port
    :return: boolean whether the port is terminated or not
    """
    counter = 0
    while is_open(port) and counter < configuration['REST']['timeout']:
        counter += 1
        time.sleep(1)
    return counter < configuration['REST']['timeout']
