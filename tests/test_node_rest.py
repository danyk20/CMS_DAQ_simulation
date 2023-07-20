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


class TestNode:
    @pytest.mark.asyncio
    async def test_get_value(self):
        """
        Test get request on the root node
        :return:
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(configuration['URL']['protocol'] + configuration['URL']['address'] + ':20000' +
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
    process = subprocess.Popen(["python", "service.py", '--port', '20000', '--levels', '2', '--children', '3'],
                               cwd=path)
    time.sleep(2)
    yield
    process.send_signal(signal.SIGTERM)


@pytest.fixture(scope="session", autouse=True)
def do_something(request):
    os.chdir(os.path.dirname(__file__))
    original_architecture = utils.set_architecture('REST')
    request.addfinalizer(lambda: utils.set_architecture(original_architecture))
