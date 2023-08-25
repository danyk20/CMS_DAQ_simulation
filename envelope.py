import envelope_pb2
import model

from errors import ValidationError


def validator(data: envelope_pb2.White | envelope_pb2.Blue | envelope_pb2.Red | envelope_pb2.Orange, color: str):
    """
    Validate any envelope

    :param data: envelope
    :param color: type of the envelope
    :return:
    """
    if color == 'white':
        if data.action != 'get_state':
            raise ValidationError('White envelope contains wrong action', data.action)
    elif color == 'blue':
        if data.state not in model.State._member_names_:
            raise ValidationError('Blue envelope contains unsupported state', data.state)
    elif color == 'red':
        if data.type != 'Notification':
            raise ValidationError('Red envelope contains wrong type', data.type)
        if not is_valid_id(data.sender):
            raise ValidationError('Red envelope contains wrong sender', data.sender)
        if data.toState.split(".")[-1] not in model.State._member_names_:
            raise ValidationError('Red envelope contains wrong state', data.toState)
    elif color == 'orange':
        if data.type != 'Input':
            raise ValidationError('Orange envelope contains wrong type', data.type)
        if data.name not in ['Running', 'Stopped']:
            raise ValidationError('Orange envelope contains wrong name', data.sender)
        if data.name == 'Start' and 0 > float(data.parameters.chance_to_fai) > 1:
            raise ValidationError('Orange envelope contains wrong fail probability', data.parameters.chance_to_fail)


def is_valid_id(routing_key) -> bool:
    """
    Check that id contains exactly 5 digits [0-9] separated by dot and in valid range defined in configuration
    file

    :param routing_key: input to check
    :return: True if the message is valid otherwise raise ValidationError
    """
    from utils import get_port, get_configuration
    configuration: dict[str, str | dict[str, str | dict]] = get_configuration()
    port = get_port(routing_key)
    if len(port) != 5:
        raise ValidationError('Red envelope contains invalid routing key length', routing_key)
    for digit in port:
        if not '0' <= digit <= '9':
            raise ValidationError('Red envelope contains invalid routing key character', routing_key)
    routing_key = get_port(routing_key)
    if configuration['node']['port']['min'] > int(routing_key) > configuration['node']['port']['max']:
        raise ValidationError('Red envelope contains routing key out of range', routing_key)
    return True
