import asyncio
import random

import uvicorn
from fastapi import FastAPI
from datetime import datetime

import model
from client import post_start, post_stop, post_notification
from model import Node

node: Node | None = None
app = FastAPI()
IP_ADDRESS = '127.0.0.1'
SLEEPING_TIME_STARTING = 10


@app.get("/statemachine/state")
def get_state() -> dict[str, str]:
    return {"State": str(node.state)}


@app.post("/statemachine/input")
async def change_state(Start: str = None, Stop: str = None, Debug: bool = False) -> model.State:
    """
    Endpoint to change node state.

    :param Start: probability between 0 and 1 of getting into Error state
    :param Stop: any non None input means stop
    :param Debug: prints debug messages for each node (when started and when did transition)
    :return: node state after transition
    """
    if node.state == model.State.Error:
        return node.state
    if Debug:
        now = datetime.now()
        print("Node " + node.address.get_port() + " is starting at" + now.strftime(" %H:%M:%S"))
    if Start:
        node.state = model.State.Starting

        tasks = []
        for child_address in node.children:
            tasks.append(post_start(Start, child_address.get_full_address(), Debug))
        await asyncio.sleep(SLEEPING_TIME_STARTING)

        for task in tasks:
            child_state = await task
            if child_state == model.State.Error:
                node.state = model.State.Error
                return node.state

        if float(Start) > random.uniform(0, 1):
            node.state = model.State.Error
        else:
            node.state = model.State.Running

    elif Stop:
        for child_address in node.children:
            await post_stop(child_address.get_full_address(), Debug)
        node.state = model.State.Stopped
    if Debug:
        now = datetime.now()
        print("Node " + node.address.get_port() + " is in " + str(node.state) + " at" + now.strftime(" %H:%M:%S"))
    return node.state


@app.post("/notifications")
async def notify(State: str = None, Sender: str = None) -> None:
    """
    Child current state notification that is recursively propagating to the root and updating states on the way

    :param State: state of the child that sent notification
    :param Sender: child's address
    :return: None
    """
    if State:
        node.children[model.NodeAddress(Sender)].append(model.State[State.split('.')[-1]])
        node.update_state()
    if node.parent.address is None:
        return
    await post_notification(node.parent.get_full_address(), str(node.state), node.address.get_full_address())


def run(created_node: Node) -> None:
    """
    Enable API

    :param created_node: node instance that is serviced by the API
    :return: None
    """
    global node
    node = created_node
    uvicorn.run(app, host=IP_ADDRESS, port=int(node.address.get_port()))
