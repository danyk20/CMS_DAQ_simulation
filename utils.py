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
