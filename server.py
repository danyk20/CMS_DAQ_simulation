import asyncio
import signal
import time

import uvicorn
from fastapi import FastAPI, HTTPException
from datetime import datetime

import model
from client import post_notification
from model import Node
from utils import get_configuration

node: Node | None = None
app = FastAPI()
configuration: dict[str, str | dict[str, str | dict]] = get_configuration()


@app.on_event("startup")
async def initialised() -> None:
    """
    Method executed when API is fully initialized, notify its parent about being redy

    :return: None
    """
    if not node.children:
        node.state = model.State.Stopped
    await post_notification(node.get_parent().get_full_address(), str(model.State.Stopped),
                            node.address.get_full_address())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Send SIGTERM to all children before termination and wait up 20s for child termination if not set other limit

    :return: None
    """
    if node:
        sleeping_time = 0
        max_sleep = configuration['node']['time']['shutdown']
        for process in node.started_processes:
            process.send_signal(signal.SIGTERM)
        for process in node.started_processes:
            sleeping_time = 0
            while process.poll is None and sleeping_time < max_sleep:
                await asyncio.sleep(1)
                sleeping_time += 1
        if sleeping_time < max_sleep:
            print('No running child processes')
        else:
            print('Child process might still run!')
        print(node.address.get_full_address() + ' is going to be terminated!')
    await asyncio.sleep(1)  # only to see termination messages from children in IDE


@app.get(configuration['URL']['get_state'])
def get_state() -> dict[str, str]:
    time.sleep(configuration['node']['time']['get'])
    return {"State": str(node.state)}


@app.post(configuration['URL']['change_state'])
async def change_state(start: str = None, stop: str = None) -> model.State:
    """
    Endpoint to change node state.

    :param start: probability between 0 and 1 of getting into Error state
    :param stop: any non None input means stop
    :return: node state after transition
    """
    if configuration['debug'] == 'True':
        now = datetime.now()
        print("Node " + node.address.get_port() + " received POST " + now.strftime(" %H:%M:%S"))
    if node.state == model.State.Error:
        return node.state
    if start and node.state == model.State.Stopped:
        node.state = model.State.Starting
        asyncio.create_task(
            node.set_state(model.State.Running, float(start), configuration['node']['time']['starting']))
    elif stop and node.state == model.State.Running:
        asyncio.create_task(
            node.set_state(model.State.Stopped, transition_time=configuration['node']['time']['starting']))
    else:
        raise HTTPException(status_code=400, detail="Combination of current state and transition state is not allowed!")
    return node.state


@app.post(configuration['URL']['notification'])
async def notify(state: str = None, sender: str = None) -> None:
    """
    Child current state notification that is recursively propagating to the root and updating states on the way

    :param state: state of the child that sent notification
    :param sender: child's address
    :return: None
    """
    if state:
        node.children[model.NodeAddress(sender)].append(model.State[state.split('.')[-1]])
        node.update_state()
    if node.get_parent().address is None:
        return
    await post_notification(node.get_parent().get_full_address(), str(node.state), node.address.get_full_address())


def run(created_node: Node) -> None:
    """
    Enable API

    :param created_node: node instance that is serviced by the API
    :return: None
    """
    global node
    node = created_node
    uvicorn.run(app, host=configuration['URL']['address'], port=int(node.address.get_port()))
