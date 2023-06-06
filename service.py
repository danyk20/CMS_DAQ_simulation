import argparse


def parse_input_arguments():
    parser = argparse.ArgumentParser(description='Process node input arguments.')
    parser.add_argument('--port', dest='port', action='store', default=20000, help='port for root node')
    parser.add_argument('--levels', dest='levels', action='store', default=4,
                        help='number of hierarchies/levels in three structure')
    parser.add_argument('--children', dest='children', action='store', default=0,
                        help='number of children per node except the leaves')
    parser.add_argument('--parent', dest='parent', action='store', default=None,
                        help='link to the parent node, keep empty')
    args = parser.parse_args()
    return args


print(parse_input_arguments().port)
