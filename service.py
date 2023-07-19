import argparse
import asyncio
import concurrent.futures
import os
import signal
import sys
from asyncio import Future
from subprocess import Popen

import receive
import server
import model
from utils import check_address, get_configuration

configuration: dict[str, str | dict[str, str | dict]] = get_configuration()


def parse_input_arguments() -> argparse.Namespace:
    """
    Parse command line arguments from following format:
    `python service.py --port 21000 --levels 1 --children 3 --parent "127.0.0.1:20000"`
    In case of invalid input it throws error and print valid range, in case of missing option it returns default values

    :return: object having 4 attributes:
        -port: integer [10 000-60 000]
            - default: 20 000
        -levels: integer [0-4]
            - default: 0
        -children: integer [1-9]
            - default: 3
        -parent: string "<IP>:<port>"
            - default: None
    """
    parser = argparse.ArgumentParser(description='Process node input arguments.')
    parser.add_argument('--port', dest='port', action='store', type=int,
                        choices=range(configuration['node']['port']['min'], configuration['node']['port']['max']),
                        default=configuration['node']['port']['default'],
                        help='port for root node')
    parser.add_argument('--levels', dest='levels', action='store', type=int,
                        choices=range(configuration['node']['depth']['min'], configuration['node']['depth']['max']),
                        default=configuration['node']['depth']['default'],
                        help='number of hierarchies/levels in three structure')
    parser.add_argument('--children', dest='children', action='store', type=int,
                        choices=range(configuration['node']['children']['min'],
                                      configuration['node']['children']['max']),
                        default=configuration['node']['children']['default'],
                        help='number of children per node except the leaves')
    parser.add_argument('--parent', dest='parent', action='store', type=check_address, default=None,
                        help='link to the parent node, keep empty')
    args = parser.parse_args()
    return args


def create_node() -> model.Node:
    """
    Creates a node instance based on given arguments

    :return: Node instance
    """
    cmd_arguments: argparse.Namespace = parse_input_arguments()
    new_node_address: str = configuration['URL']['address'] + ':' + str(cmd_arguments.port)
    model.Node.arity = cmd_arguments.children
    model.Node.depth = cmd_arguments.levels
    return model.Node(model.NodeAddress(new_node_address))


def create_children(parent: model.Node) -> None:
    """
    Recursively create child nodes which are defined in parent node attribute children

    :return: None
    """
    for child_address in parent.children:
        process: Popen = Popen(
            ['python', 'service.py', '--port', str(child_address.get_port()), '--levels', str(model.Node.depth),
             '--children', str(model.Node.arity), '--parent', parent.address.get_full_address()])
        node.started_processes.append(process)


server_task: None | Future[None] = None
receiver_task: None | Future[None] = None


async def setup() -> None:
    """
    Starts MOM consumer and rpc server running in infinite asynchronous loop and handle task cancellation

    :return: None
    """
    global receiver_task, server_task
    loop = asyncio.get_running_loop()
    run_consumer = lambda: receive.run(node, loop)
    rpc_server = lambda: node.run_get_server()

    with concurrent.futures.ThreadPoolExecutor() as pool:
        receiver_task = loop.run_in_executor(pool, run_consumer)
        server_task = loop.run_in_executor(pool, rpc_server)
        try:
            await receiver_task
        except asyncio.CancelledError:
            if configuration['debug']:
                print('Consumer ' + node.address.get_port() + ' stopped')
        try:
            await server_task
        except asyncio.CancelledError:
            if configuration['debug']:
                print('RPC server ' + node.address.get_port() + ' stopped')
        if configuration['debug']:
            print('Node ' + node.address.get_port() + ' is terminated')


async def shutdown_event(broker_disconnect: bool = True) -> None:
    """
    Send SIGTERM to all children before termination and wait up Xs for child termination if not set other limit

    :param broker_disconnect: whether kill process inside the function forcefully
    :return: None
    """
    if node:
        sleeping_time = 0
        max_sleep = configuration['node']['time']['shutdown']
        for process in node.started_processes:
            process.send_signal(signal.SIGTERM)
        for process in node.started_processes:
            sleeping_time = 0
            while process.poll() is None and sleeping_time < max_sleep:
                await asyncio.sleep(1)
                sleeping_time += 1
        if configuration['debug']:
            if sleeping_time < max_sleep:
                print('No running child processes')
            else:
                print('Child process might still run!')
            print(node.address.get_full_address() + ' is going to be terminated!')
        if broker_disconnect:
            node.kill_consumer()
            node.kill_rpc_serer()
            loop = asyncio.get_running_loop()
            server_task.cancel()
            receiver_task.cancel()
            loop.call_soon_threadsafe(loop.stop)
    await asyncio.sleep(1)  # only to see termination messages from children in IDE


if configuration['debug']:
    print('My PID is:', os.getpid())
node: model.Node = create_node()
create_children(node)
if configuration['architecture'] == 'MOM':
    async_loop = asyncio.get_event_loop()
    async_loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(shutdown_event()))
    async_loop.create_task(setup())
    async_loop.run_forever()
    # why is it necessary
    sys.exit(0)
elif configuration['architecture'] == 'REST':
    server.run(node, shutdown=shutdown_event)
