import aiohttp
import json
import os
import pytest
import signal
import subprocess
import time

import utils
import model

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
        :return:
        """
        ports = list(get_all_ports())
        ports.sort()
        for port in ports:
            async with aiohttp.ClientSession() as session:
                async with session.get(configuration['URL']['protocol'] + configuration['URL']['address'] + ':' + port +
                                       configuration['URL']['get_state']) as resp:
                    assert resp.status == 200
                    assert json.loads(await resp.text()) == {"State": "State.Stopped"}


def generate_node(state: model.State, address: str = '127.0.0.0:20000',
                  children: dict[model.NodeAddress, [model.State]] = None) -> model.Node:
    node_add = model.NodeAddress(address)
    node = model.Node(node_add)
    node.state = state
    if children:
        node.children = children
    return node


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
