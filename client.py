import aiohttp

CHANGE_STATE_ENDPOINT = '/statemachine/input'
NOTIFICATIONS_ENDPOINT = '/notifications'


async def post_start(chance_to_fail: str, address: str):
    async with aiohttp.ClientSession() as session:
        params = {'Start': str(chance_to_fail)}
        async with session.post('http://' + address + CHANGE_STATE_ENDPOINT, params=params) as _:
            pass


async def post_stop(address: str):
    async with aiohttp.ClientSession() as session:
        params = {'Stop': ''}
        async with session.post('http://' + address + CHANGE_STATE_ENDPOINT, params=params) as _:
            pass


async def post_notification(address: str, state: str):
    async with aiohttp.ClientSession() as session:
        params = {'State': state}
        async with session.post('http://' + address + NOTIFICATIONS_ENDPOINT, params=params) as _:
            pass
