import argparse

from utils import check_address


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
