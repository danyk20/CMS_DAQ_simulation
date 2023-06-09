import argparse
from subprocess import Popen

import server
from model import Node, NodeAddress
from utils import check_address

IP_ADDRESS = '127.0.0.1'


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
    parser.add_argument('--port', dest='port', action='store', type=int, choices=range(10000, 60000), default=20000,
                        help='port for root node')
    parser.add_argument('--levels', dest='levels', action='store', type=int, choices=range(0, 5), default=0,
                        help='number of hierarchies/levels in three structure')
    parser.add_argument('--children', dest='children', action='store', type=int, choices=range(1, 10), default=3,
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
    configuration: argparse.Namespace = parse_input_arguments()
    root_address: str = IP_ADDRESS + ':' + str(configuration.port)
    Node.arity = configuration.children
    Node.depth = configuration.levels
    return Node(NodeAddress(root_address), NodeAddress(configuration.parent))


def create_children(parent: Node):
    """
    Recursively create child nodes which are defined in parent node attribute children

    :return: None
    """
    for child_address in parent.children:
        Popen(
            ['python', 'service.py', '--port', str(child_address.get_port()), '--levels', str(Node.depth),
             '--children', str(Node.arity), '--parent', parent.address.get_full_address()])


node: Node = create_node()
create_children(node)
server.run(node)
