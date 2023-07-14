import aiohttp

from utils import get_configuration

configuration: dict[str, str | dict] = get_configuration()


async def post_start(chance_to_fail: str, address: str) -> None:
    """
    Sends asynchronous post request to the specific node in order to change it's state to Running or Error

    :param chance_to_fail: string representation of decimal number between 0 and 1
    :param address: node address
    :return: None
    """
    async with aiohttp.ClientSession() as session:
        params = {'start': str(chance_to_fail)}
        if configuration['debug'] == 'True':
            params["debug"] = 'True'
        async with session.post(configuration['URL']['protocol'] + address + configuration['URL']['change_state'],
                                params=params) as _:
            pass


async def post_stop(address: str) -> None:
    """
    Sends asynchronous post request to the specific node in order to change it's state to Stop

    :param address: node address
    :return: None
    """
    async with aiohttp.ClientSession() as session:
        params = {'stop': ' '}
        if configuration['debug'] == 'True':
            params["debug"] = 'True'
        async with session.post(configuration['URL']['protocol'] + address + configuration['URL']['change_state'],
                                params=params) as _:
            pass


async def post_notification(receiver_address: str, state: str, sender_address: str) -> None:
    """

    :param receiver_address: to which node is notification going
    :param state: node state
    :param sender_address: from which node is notification coming from
    :return: None
    """
    if receiver_address:
        async with aiohttp.ClientSession() as session:
            params = {'state': state, 'sender': sender_address}
            async with session.post(
                    configuration['URL']['protocol'] + receiver_address + configuration['URL']['notification'],
                    params=params) as _:
                pass
