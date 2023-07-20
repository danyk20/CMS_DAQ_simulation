import asyncio

import aiohttp
import json
import os
import pytest
import signal
import subprocess
import time

import utils

pytest_plugins = ('pytest_asyncio',)
configuration: dict[str, str | dict[str, str | dict]] = utils.get_configuration()

CHILDREN = '3'
LEVELS = '2'
PORT = '20000'


class TestNode:
    @pytest.mark.asyncio
    async def test_get_value(self):
        """
        Test get request from all nodes
        :return: None
        """
        ports = list(get_all_ports())
        ports.sort()
        for port in ports:
            async with aiohttp.ClientSession() as session:
                async with session.get(configuration['URL']['protocol'] + configuration['URL']['address'] + ':' + port +
                                       configuration['URL']['get_state']) as resp:
                    assert resp.status == 200
                    assert json.loads(await resp.text()) == {"State": "State.Stopped"}

    @pytest.mark.asyncio
    async def test_get_duration(self):
        """
        Test get request time duration
        :return: None
        """
        async with aiohttp.ClientSession() as session:
            start = time.time()
            async with session.get(configuration['URL']['protocol'] + configuration['URL']['address'] + ':' + PORT +
                                   configuration['URL']['get_state']) as _:
                end = time.time()
                duration = end - start
                starting_time = configuration['node']['time']['get']
                assert starting_time - 1 < duration < starting_time + 1

    @pytest.mark.asyncio
    async def test_middle_node_interaction(self):
        """
        Complex test testing change state propagation to children and also notification propagation to the parent
        :return:
        """
        params = {'start': '1'}
        error_initiator = sorted(list(get_children_ports(PORT)))[0]
        await asyncio.sleep(1)
        async with aiohttp.ClientSession() as session:
            # set error statin in most left child pof the root
            async with session.post(configuration['URL']['protocol'] + configuration['URL']['address'] + ':' +
                                    error_initiator + configuration['URL']['change_state'], params=params) as _:
                await asyncio.sleep(configuration['node']['time']['starting'] + 1)
                # check that error was propagated to the top
                async with session.get(configuration['URL']['protocol'] + configuration['URL']['address'] + ':' + PORT +
                                       configuration['URL']['get_state']) as resp:
                    assert json.loads(await resp.text()) == {"State": "State.Error"}
                # check that node most left root node is in error state
                async with session.get(
                        configuration['URL']['protocol'] + configuration['URL']['address'] + ':' + error_initiator +
                        configuration['URL']['get_state']) as resp:
                    assert json.loads(await resp.text()) == {"State": "State.Error"}
                # check that all its children are in error state
                for port in get_children_ports(error_initiator, 2):
                    async with session.get(
                            configuration['URL']['protocol'] + configuration['URL']['address'] + ':' + port +
                            configuration['URL']['get_state']) as resp:
                        assert json.loads(await resp.text()) == {"State": "State.Error"}
                # all other nodes are stopped
                stopped_nodes = (get_children_ports(PORT).difference({error_initiator})).difference(
                    get_children_ports(error_initiator, 2))
                for port in stopped_nodes:
                    async with session.get(
                            configuration['URL']['protocol'] + configuration['URL']['address'] + ':' + port +
                            configuration['URL']['get_state']) as resp:
                        assert json.loads(await resp.text()) == {"State": "State.Stopped"}


@pytest.fixture(autouse=True)
def run_around_tests():
    path = os.path.join(os.getcwd(), '..')
    process = subprocess.Popen(["python", "service.py", '--port', PORT, '--levels', LEVELS, '--children', CHILDREN],
                               cwd=path)
    time.sleep(2)
    yield
    process.send_signal(signal.SIGTERM)


@pytest.fixture(scope="session", autouse=True)
def do_something(request):
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
