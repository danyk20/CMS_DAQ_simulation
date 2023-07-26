import argparse
import yaml
import json
import os

import envelope_pb2


def check_address(address: str) -> str:
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


def get_configuration_full_path() -> str:
    """
    Get absolut path to the configuration file
    :return: Absolut path to the configuration file
    """
    dir_path = os.path.dirname(__file__)
    return os.path.join(dir_path, "configuration.yaml")


def get_configuration() -> dict[str, str | dict[str, str | dict]]:
    """
    Load all values from configuration.yaml into dictionary

    :return: dictionary of configuration vales
    """
    with open(get_configuration_full_path()) as stream:
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


def get_red_envelope(transitioned_state: str, sender: str = '') -> str:
    """
    Produce json format necessary for notification about the state change in the children node.

    :param transitioned_state: new current state of the child node
    :param sender: origin node id as bind key
    :return: string representation of red envelope
    """
    envelope_format = get_configuration()['rabbitmq']['envelope_format']
    if envelope_format == 'json':
        envelope = dict()
        envelope['type'] = 'Notification'
        envelope['sender'] = sender
        envelope['toState'] = transitioned_state
        return json.dumps(envelope)
    elif envelope_format == 'proto':
        red_envelope = envelope_pb2.Red()
        red_envelope.type = 'Notification'
        red_envelope.sender = sender
        red_envelope.toState = transitioned_state
        return red_envelope


def get_orange_envelope(state: str, chance_to_fail: float = 0) -> str:
    """
    Produce json format necessary for changing state selected node.

    :param state: requested new state
    :param chance_to_fail: chance to end up in Error state
    :return: string representation of orange envelope
    """
    envelope_format = get_configuration()['rabbitmq']['envelope_format']
    if envelope_format == 'json':
        envelope = dict()
        envelope['type'] = 'Input'
        envelope['name'] = state
        envelope['parameters'] = {'chance_to_fail': chance_to_fail}
        return json.dumps(envelope)
    elif envelope_format == 'proto':
        orange_envelope = envelope_pb2.Orange()
        orange_envelope.type = 'Input'
        orange_envelope.name = state
        orange_envelope.parameters.chance_to_fail = chance_to_fail
        return orange_envelope


def get_blue_envelope(current_state: str) -> str:
    """
    Produce json format for replying from rpc server.

    :param current_state: node current state
    :return: string representation of blue envelope
    """
    envelope_format = get_configuration()['rabbitmq']['envelope_format']
    if envelope_format == 'json':
        envelope = dict()
        envelope['state'] = current_state
        return json.dumps(envelope)
    elif envelope_format == 'proto':
        blue_envelope = envelope_pb2.Blue()
        blue_envelope.state = current_state
        return blue_envelope


def get_white_envelope(requested_action: str = 'get_state') -> str:
    """
    Produce json format for requesting state from rpc server.

    Note: currently the only supported operation is get_state

    :param requested_action: type of request
    :return: string representation of blue envelope
    """
    envelope_format = get_configuration()['rabbitmq']['envelope_format']
    if envelope_format == 'json':
        envelope = dict()
        envelope['action'] = requested_action
        return json.dumps(envelope)
    elif envelope_format == 'proto':
        white_envelope = envelope_pb2.White()
        white_envelope.action = requested_action
        return white_envelope


def set_architecture(architecture: str):
    """
    Edit selected architecture in configuration file
    :param architecture: newly selected architecture
    :return: original architecture
    """
    with open(get_configuration_full_path()) as f:
        list_doc = yaml.safe_load(f)

    original_architecture = list_doc['architecture']
    if original_architecture != architecture:
        list_doc['architecture'] = architecture
        with open(get_configuration_full_path(), "w") as f:
            yaml.dump(list_doc, f)

    return original_architecture


def set_time(time: str, value: int):
    """
    Edit selected architecture in configuration file
    :param value: newly selected value
    :param time: specifier
    :return: original architecture
    """
    with open(get_configuration_full_path()) as f:
        list_doc = yaml.safe_load(f)

    original_value = list_doc['node']['time'][time]
    if original_value != value:
        list_doc['node']['time'][time] = value
        with open(get_configuration_full_path(), "w") as f:
            yaml.dump(list_doc, f)

    return original_value
