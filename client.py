import asyncio

import aiohttp
from aiohttp import ClientConnectorError

from utils import get_configuration

configuration: dict[str, str | dict] = get_configuration()


async def post_start(chance_to_fail: str, address: str) -> None:
    """
    Sends asynchronous post request to the specific node in order to change it's state to Running or Error

    :param chance_to_fail: string representation of decimal number between 0 and 1
    :param address: node address
    :return: None
    """
    endpoint = address + configuration['URL']['change_state']
    params = {'start': str(chance_to_fail)}
    await request_node(endpoint, params)


async def post_stop(address: str) -> None:
    """
    Sends asynchronous post request to the specific node in order to change it's state to Stop

    :param address: node address
    :return: None
    """
    params = {'stop': ' '}
    endpoint = address + configuration['URL']['change_state']
    await request_node(endpoint, params)


async def post_notification(address: str, state: str, sender_address: str) -> None:
    """

    :param address: to which node is notification going
    :param state: node state
    :param sender_address: from which node is notification coming from
    :return: None
    """

    if address:
        params = {'state': state, 'sender': sender_address}
        endpoint = address + configuration['URL']['notification']
        await request_node(endpoint, params)


async def request_node(endpoint, params) -> None:
    """
    General HTTP post request to specific node with parameters
    :param endpoint: node address, port and path
    :param params: attributes
    :return: None
    """
    delivered = False
    attempts = 0
    url = configuration['URL']['protocol'] + endpoint
    async with aiohttp.ClientSession() as session:
        while not delivered:
            if attempts > configuration['REST']['timeout']:
                if configuration['debug']:
                    print(str(params) + ' - message cannot be delivered to ' + url)
                return
            try:
                async with session.post(url, params=params) as request:
                    if request.status == 200:
                        return
                    else:
                        raise Exception("Server didn't responded as expected")
            except (ClientConnectorError, Exception):
                await asyncio.sleep(1)
                attempts += 1
