import requests

from send import post_state_change, post_state_notification
from utils import get_configuration

configuration: dict[str, str | dict[str, str | dict]] = get_configuration()


# Note: Example assume the default configuration so it allways starts with 2 levels 3 children and port 20000 (Stopped)

def post_empty_change_state() -> int:
    """
    Show example of corrupted message - empty
    :return: 400 code
    """
    message = {}
    response_code = post(configuration['URL']['change_state'], message)
    print(response_code)
    return response_code


def post_invalid_change_state() -> int:
    """
    Show example of correct message but invalid state change
    :return: 400 code
    """
    message = {'stop': '_'}
    response_code = post(configuration['URL']['change_state'], message)
    print(response_code)
    return response_code


def post_unknown_change_state() -> int:
    """
    Show example of corrupted message - non-existing
    :return: 400 code
    """
    message = {'foo': '_'}
    response_code = post(configuration['URL']['change_state'], message)
    print(response_code)
    return response_code


def post_extra_change_state() -> int:
    """
    Show example of corrupted message - extra argument
    :return: 200 code
    """
    message = {'foo': '_', 'start': '0'}
    response_code = post(configuration['URL']['change_state'], message)
    print(response_code)
    return response_code


def post_valid_change_state() -> int:
    """
    Show example of corrupted message - extra argument
    :return: 200 code
    """
    message = {'start': '0'}
    response_code = post(configuration['URL']['change_state'], message)
    print(response_code)
    return response_code


def post(endpoint: str, message: dict) -> int:
    """
    General post request to the default root node

    :param endpoint: endpoint name
    :param message: json
    :return: 200 or 400 code
    """
    url = configuration['URL']['protocol'] + configuration['URL']['address'] + ':20000' + endpoint

    response = requests.post(url, params=message)

    return response.status_code


def send_invalid_state_mom() -> None:
    """
    Sends command to change the state but the parameter is invalid therefore it will be ignored.

    :return: None
    """
    post_state_change('invalid', '2.0.0.0.0')


def send_invalid_notification_mom() -> None:
    """
    Sends notification to the root node but the parameter is invalid therefore it will be ignored.

    :return: None
    """
    post_state_notification('state.invalid', '2.0.0.0.0', '2.1.0.0.0')
