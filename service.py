import argparse
from subprocess import Popen

import server
from model import Node, NodeAddress
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


def create_node() -> Node:
    """
    Creates a node instance based on given arguments

    :return: Node instance
    """
    cmd_arguments: argparse.Namespace = parse_input_arguments()
    new_node_address: str = configuration['URL']['address'] + ':' + str(cmd_arguments.port)
    Node.arity = cmd_arguments.children
    Node.depth = cmd_arguments.levels
    return Node(NodeAddress(new_node_address))


def create_children(parent: Node) -> None:
    """
    Recursively create child nodes which are defined in parent node attribute children

    :return: None
    """
    for child_address in parent.children:
        process: Popen = Popen(
            ['python', 'service.py', '--port', str(child_address.get_port()), '--levels', str(Node.depth),
             '--children', str(Node.arity), '--parent', parent.address.get_full_address()])
        node.started_processes.append(process)


node: Node = create_node()
create_children(node)
server.run(node)
