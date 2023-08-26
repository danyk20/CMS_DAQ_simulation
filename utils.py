import argparse
import sys

import yaml
import json
import os

from google.protobuf.json_format import MessageToDict

import envelope_pb2
from errors import ValidationError


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
    :return: string value of binding key if port is not None
    """
    if port:
        return '.'.join(list(port))


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
        envelope = {'color': 'red', 'type': 'Notification', 'sender': sender, 'toState': transitioned_state}
        return json.dumps(envelope)
    elif envelope_format == 'proto':
        envelope = envelope_pb2.Rainbow()
        envelope.color = 'red'
        envelope.red.type = 'Notification'
        envelope.red.sender = sender
        envelope.red.toState = transitioned_state

        return envelope.SerializeToString()


def get_orange_envelope(state: str, chance_to_fail: float = 0) -> str:
    """
    Produce json format necessary for changing state selected node.

    :param state: requested new state
    :param chance_to_fail: chance to end up in Error state
    :return: string representation of orange envelope
    """
    envelope_format = get_configuration()['rabbitmq']['envelope_format']
    if envelope_format == 'json':
        envelope = {'color': 'orange', 'type': 'Input', 'name': state, 'parameters': {'chance_to_fail': chance_to_fail}}
        return json.dumps(envelope)
    elif envelope_format == 'proto':
        envelope = envelope_pb2.Rainbow()
        envelope.color = 'orange'
        envelope.orange.type = 'Input'
        envelope.orange.name = state
        envelope.orange.parameters.chance_to_fail = chance_to_fail
        return envelope.SerializeToString()


def get_blue_envelope(current_state: str) -> str:
    """
    Produce json format for replying from rpc server.

    :param current_state: node current state
    :return: string representation of blue envelope
    """
    envelope_format = get_configuration()['rabbitmq']['envelope_format']
    if envelope_format == 'json':
        envelope = {'color': 'blue', 'state': current_state}
        return json.dumps(envelope)
    elif envelope_format == 'proto':
        envelope = envelope_pb2.Rainbow()
        envelope.color = 'blue'
        envelope.blue.state = current_state
        return envelope.SerializeToString()


def get_white_envelope(requested_action: str = 'get_state') -> str:
    """
    Produce json format for requesting state from rpc server.

    Note: currently the only supported operation is get_state

    :param requested_action: type of request
    :return: string representation of white envelope
    """
    envelope_format = get_configuration()['rabbitmq']['envelope_format']
    if envelope_format == 'json':
        envelope = {'color': 'white', 'action': requested_action}
        return json.dumps(envelope)
    elif envelope_format == 'proto':
        envelope = envelope_pb2.Rainbow()
        envelope.color = 'white'
        envelope.white.action = requested_action
        return envelope.SerializeToString()


def set_architecture(architecture: str) -> str:
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


def set_message_format(new_format: str) -> str:
    """
    Edit selected architecture in configuration file

    :param new_format: newly selected architecture
    :return: original envelope format
    """

    return set_configuration(new_format, ['rabbitmq', 'envelope_format'])


def set_configuration(new_value: str | bool | int, path: list) -> str | int:
    """
    Edit selected value in configuration file

    :param path: path to get the selected value
    :param new_value: newly selected value
    :return: original value
    """
    with open(get_configuration_full_path()) as f:
        list_doc = yaml.safe_load(f)

    reference = list_doc
    original_value = ''

    for i in range(len(path)):
        if i < len(path) - 1:
            reference = reference[path[i]]
        else:
            original_value = reference[path[i]]
    if original_value != new_value:
        reference[path[-1]] = new_value
        with open(get_configuration_full_path(), "w") as f:
            yaml.dump(list_doc, f)

    return original_value


def set_time(time: str, value: int) -> int:
    """
    Edit selected architecture in configuration file

    :param value: newly selected value
    :param time: specifier
    :return: original value
    """
    with open(get_configuration_full_path()) as f:
        list_doc = yaml.safe_load(f)

    original_value = list_doc['node']['time'][time]
    if original_value != value:
        list_doc['node']['time'][time] = value
        with open(get_configuration_full_path(), "w") as f:
            yaml.dump(list_doc, f)

    return original_value


def get_dict_from_envelope(message: str, accepted_types: list = ['white', 'blue', 'red', 'orange']) -> dict:
    """
    Convert string data (envelope) to dictionary

    :param accepted_types: which envelope type can be accepted
    :param message: data to convert
    :return: dictionary with key = envelope attribute and its value
    """
    import envelope as env

    if get_configuration()['rabbitmq']['envelope_format'] == 'json':
        return json.loads(message)
    envelope = envelope_pb2.Rainbow()
    envelope.ParseFromString(message)

    if envelope.color not in accepted_types:
        raise ValidationError('Unexpected envelope type arrived')

    if envelope.color == 'white':
        data = envelope.white
    elif envelope.color == 'orange':
        data = envelope.orange
    elif envelope.color == 'red':
        data = envelope.red
    elif envelope.color == 'blue':
        data = envelope.blue
    else:
        raise ValidationError('Unsupported envelope type arrived')
    if get_configuration()['rabbitmq']['validation']:
        env.validator(data, envelope.color)

    return MessageToDict(data, preserving_proto_field_name=True)


def exception_filter(func):
    """
    Execute function and print Validation Error in case it occurs

    :param func: function to execute
    :return: return value of the function
    """
    try:
        return func()
    except ValidationError as e:
        if e.errors:
            print(e.errors, file=sys.stderr)
        print(e.args[0], file=sys.stderr)
