import asyncio
import random

import uvicorn
from fastapi import FastAPI
from datetime import datetime

import model
from client import post_start, post_stop, post_notification
from model import Node
from utils import get_configuration

node: Node | None = None
app = FastAPI()
configuration: dict[str, str | dict[str, str | dict]] = get_configuration()


@app.on_event("shutdown")
def shutdown_event() -> None:
    """
    All necessary calls that need to be executed before shutdown

    :return: None
    """
    if node:
        print(node.address.get_full_address() + " is going to be terminated!")


@app.get("/statemachine/state")
def get_state() -> dict[str, str]:
    return {"State": str(node.state)}


@app.post("/statemachine/input")
async def change_state(start: str = None, stop: str = None, debug: bool = False) -> model.State:
    """
    Endpoint to change node state.

    :param start: probability between 0 and 1 of getting into Error state
    :param stop: any non None input means stop
    :param debug: prints debug messages for each node (when started and when did transition)
    :return: node state after transition
    """
    if node.state == model.State.Error:
        return node.state
    if debug:
        now = datetime.now()
        print("Node " + node.address.get_port() + " is starting at" + now.strftime(" %H:%M:%S"))
    if start:
        node.state = model.State.Starting

        tasks = []
        await asyncio.sleep(configuration['node']['time']['starting'])
        for child_address in node.children:
            tasks.append(asyncio.create_task(post_start(start, child_address.get_full_address(), debug)))

        for task in tasks:
            child_state = await task
            if child_state == model.State.Error:
                node.state = model.State.Error
                return node.state

        if float(start) > random.uniform(0, 1):
            node.state = model.State.Error
        else:
            node.state = model.State.Running
            node.chance_to_fail = float(start)
            asyncio.create_task(node.run(notification=notify, debug=debug))

    elif stop:
        for child_address in node.children:
            await post_stop(child_address.get_full_address(), debug)
        node.state = model.State.Stopped
    if debug:
        now = datetime.now()
        print("Node " + node.address.get_port() + " is in " + str(node.state) + " at" + now.strftime(" %H:%M:%S"))
    return node.state


@app.post("/notifications")
async def notify(state: str = None, sender: str = None) -> None:
    """
    Child current state notification that is recursively propagating to the root and updating states on the way

    :param state: state of the child that sent notification
    :param sender: child's address
    :return: None
    """
    if state:
        if model.NodeAddress(sender) not in node.children:
            node.children[model.NodeAddress(sender)] = [model.State[state.split('.')[-1]]]
        else:
            node.children[model.NodeAddress(sender)].append(model.State[state.split('.')[-1]])
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
    uvicorn.run(app, host=configuration['URL']['address'], port=int(node.address.get_port()))
