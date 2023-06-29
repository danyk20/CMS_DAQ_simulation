import argparse
import string

import yaml


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
    configuration: dict[str, str | dict[str, str | dict]] = get_configuration()
    if int(port) < configuration['node']['port']['min'] or int(port) >= configuration['node']['port']['max']:
        raise argparse.ArgumentTypeError("%s is out of range valid port values" % port)
    return address


def compute_hierarchy_level(port: str) -> int:
    """
    Computes hierarchical node level based on given parent port number. In case of NONE value it return 0 (root node)

    :param port: port number represented by string
    :return: integer number representing level from top to bottom where root is 0
    """
    if '0' in port:
        return port.index('0') - 1
    else:
        return 4


def get_configuration() -> dict[str, str | dict[str, str | dict]]:
    """
    Load all values from configuration.yaml into dictionary

    :return: dictionary of configuration vales
    """
    with open("configuration.yaml", 'r') as stream:
        try:
            parsed_yaml = yaml.safe_load(stream)
            return parsed_yaml
        except yaml.YAMLError as exc:
            print(exc)


def get_bounding_key(port: str) -> str:
    """
    Convert port into associated binding key

    :param port: number in string format
    :return: string value of binding key
    """
    if port:
        return '.'.join(list(port))
    return ''


def get_port(bounding_key: str) -> str:
    """
    Convert binding key into associated port

    :param bounding_key: string value of binding key
    :return: number in string format
    """
    if bounding_key:
        return ''.join(bounding_key.split('.'))
    return ''
