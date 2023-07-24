import asyncio

import aiohttp
import json
import os
import pytest
import signal
import subprocess
import time

from aiohttp import ClientConnectorError

import utils

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

        await post_state(start)
        await asyncio.sleep(configuration['node']['time']['starting'] + 1)
        assert await get_state() == {"State": "State.Running"}

        await post_state(stop)
        await asyncio.sleep(configuration['node']['time']['starting'] + 1)
        assert await get_state() == {"State": "State.Stopped"}

        await post_state(error)
        await asyncio.sleep(configuration['node']['time']['starting'] + 1)
        assert await get_state() == {"State": "State.Error"}

    @pytest.mark.asyncio
    @pytest.mark.usefixtures('run_around_tests')
    async def test_middle_node_interaction(self):
        """
        Complex test testing change state propagation to children and also notification propagation to the parent
        :return: None
        """
        params = {'start': '1'}
        error_initiator = sorted(list(get_children_ports(PORT)))[0]
        await post_state(params, error_initiator)
        await asyncio.sleep(configuration['node']['time']['starting'] + 1)
        assert await get_state() == {"State": "State.Error"}
        assert await get_state(error_initiator) == {"State": "State.Error"}
        # check that all its children are in error state
        for port in get_children_ports(error_initiator, 2):
            assert await get_state(port) == {"State": "State.Error"}
        # all other nodes are stopped
        stopped_nodes = (get_children_ports(PORT).difference({error_initiator})).difference(
            get_children_ports(error_initiator, 2))
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


@pytest.fixture(scope="session", autouse=True)
def configure_configuration_file(request):
    os.chdir(os.path.dirname(__file__))
    original_architecture = utils.set_architecture('REST')
    request.addfinalizer(lambda: utils.set_architecture(original_architecture))


def get_children_ports(parent_port: str, level: int = 1):
    ports = set()
    for child in range(int(CHILDREN)):
        node_port = list(parent_port)
        node_port[level] = str(child + 1)
        ports.add(''.join(node_port))

    for port in ports:
        if level < int(LEVELS):
            ports = ports.union(get_children_ports(port, level + 1))
    return ports


def get_all_ports():
    ports = get_children_ports(PORT)
    ports.add(PORT)
    return ports


async def get_state(port: str = PORT) -> str:
    counter = 0
    while (True):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        configuration['URL']['protocol'] + configuration['URL']['address'] + ':' + port +
                        configuration['URL']['get_state']) as resp:
                    assert resp.status == 200
                    return json.loads(await resp.text())
        except ClientConnectorError:
            time.sleep(1)
            counter += 1
            if counter > configuration['REST']['timeout']:
                return ""


async def post_state(param: dict, port: str = PORT) -> None:
    counter = 0
    while (True):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(configuration['URL']['protocol'] + configuration['URL']['address'] + ':' +
                                        port + configuration['URL']['change_state'], params=param) as request:
                    if request.status == 200:
                        break
        except ClientConnectorError:
            time.sleep(1)
            counter += 1
            if counter > configuration['REST']['timeout']:
                return
