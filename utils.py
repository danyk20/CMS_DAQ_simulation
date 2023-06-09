import argparse
import string


def check_address(address: string) -> string:
    """
    Validate whether address is in correct format, otherwise throw an error.

    :param address: string in format IP:port
    :return: unmodified address
    """
    if len(address.split(':')) != 2:
        raise argparse.ArgumentTypeError("%s is not in correct IP:port format" % address)
    ip = address.split(':')[0]
    port = address.split(':')[1]
    if len(ip.split('.')) != 4 or any(0 > int(octet) or int(octet) > 255 for octet in ip.split('.')):
        raise argparse.ArgumentTypeError("%s is an invalid IP address value" % ip)
    if int(port) < 10000 or int(port) >= 60000:
        raise argparse.ArgumentTypeError("%s is out of range valid port values" % port)
    return address


def compute_hierarchy_level(parent_port: str) -> int:
    '''
    Computes hierarchical node level based on given parent port number. In case of NONE value it return 0 (root node)

    :param parent_port: port number represented by string
    :return: integer number representing level from top to bottom where root is 0
    '''
    if parent_port:
        return parent_port.index('0')
    else:
        return 0
