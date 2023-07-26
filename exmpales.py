import requests

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


def post(endpoint: str, message: dict):
    """
    General post request to the default root node

    :param endpoint: endpoint name
    :param message: json
    :return: 200 or 400 code
    """
    url = configuration['URL']['protocol'] + configuration['URL']['address'] + ':20000' + endpoint

    response = requests.post(url, params=message)

    return response.status_code
