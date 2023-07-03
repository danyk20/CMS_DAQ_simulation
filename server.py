import asyncio
import time

import uvicorn
from fastapi import FastAPI, HTTPException
from datetime import datetime

import model
import service
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
    Call default shutdown method but don't kill process by this function

    :return: None
    """
    await service.shutdown_event(False)


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
