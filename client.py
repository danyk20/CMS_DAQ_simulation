import aiohttp

CHANGE_STATE_ENDPOINT = '/statemachine/input'
NOTIFICATIONS_ENDPOINT = '/notifications'
PROTOCOL = 'http://'


async def post_start(chance_to_fail: str, address: str, debug: bool) -> None:
    """
    Sends asynchronous post request to the specific node in order to change it's state to Running or Error

    :param chance_to_fail: string representation of decimal number between 0 and 1
    :param address: node address
    :param debug: optional boolean to enable debug print to see start and end time of the transition
    :return: None
    """
    async with aiohttp.ClientSession() as session:
        params = {'start': str(chance_to_fail)}
        if debug:
            params["debug"] = 'True'
        async with session.post(PROTOCOL + address + CHANGE_STATE_ENDPOINT, params=params) as _:
            pass


async def post_stop(address: str, debug: bool) -> None:
    """
    Sends asynchronous post request to the specific node in order to change it's state to Stop

    :param address: node address
    :param debug: debug: optional boolean to enable debug print to see start and end time of the transition
    :return: None
    """
    async with aiohttp.ClientSession() as session:
        params = {'stop': ''}
        if debug:
            params["debug"] = 'True'
        async with session.post(PROTOCOL + address + CHANGE_STATE_ENDPOINT, params=params) as _:
            pass


async def post_notification(receiver_address: str, state: str, sender_address: str) -> None:
    """

    :param receiver_address: to which node is notification going
    :param state: node state
    :param sender_address: from which node is notification coming from
    :return: None
    """
    async with aiohttp.ClientSession() as session:
        params = {'state': state, 'sender': sender_address}
        async with session.post(PROTOCOL + receiver_address + NOTIFICATIONS_ENDPOINT, params=params) as _:
            pass
