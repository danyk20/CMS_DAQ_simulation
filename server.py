import asyncio
import sys
import time

import uvicorn
from fastapi import FastAPI, HTTPException
from datetime import datetime

import model
from typing import Callable, Optional
from client import post_notification
from message import ChangeState, Notification, ValidationError
from model import Node
from utils import get_configuration
from starlette.requests import Request
from starlette.responses import Response

node: Node | None = None
app = FastAPI()
configuration: dict[str, str | dict[str, str | dict]] = get_configuration()
shutdown_handler: Callable


async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except ValidationError as e:
        if e.errors:
            print(e.errors, file=sys.stderr)
        print(e.args[0], file=sys.stderr)
        return Response("Validation Error", status_code=400)


app.middleware('http')(catch_exceptions_middleware)


@app.on_event("startup")
async def initialised() -> None:
    """
    Method executed when API is fully initialized, notify its parent about being redy

    :return: None
    """
    if not node.children:
        node.state = model.State.Stopped
    await post_notification(node.get_parent().get_full_address(), str(node.state),
                            node.address.get_full_address())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Call default shutdown method but don't kill process by this function

    :return: None
    """
    await shutdown_handler(False)


@app.get(configuration['URL']['get_state'])
def get_state() -> dict[str, str]:
    time.sleep(configuration['node']['time']['get'])
    return {"State": str(node.state)}


@app.post(configuration['URL']['change_state'])
async def change_state(state_change_command: Optional[ChangeState] = None, start: Optional[str] = None,
                       stop: Optional[str] = None) -> model.State:
    """
    Endpoint to change node state.

    :param state_change_command: object containing validated start or stop
    :param start: probability between 0 and 1 of getting into Error state
    :param stop: any non None input means stop
    :return: node state after transition
    """
    if configuration['debug']:
        now = datetime.now()
        print("Node " + node.address.get_port() + " received POST " + now.strftime(" %H:%M:%S"))
    if node.state == model.State.Error:
        return node.state

    if configuration['REST']['pydantic']:
        prompt_to_start = state_change_command.start
        prompt_to_stop = state_change_command.stop
    else:
        prompt_to_start = start
        prompt_to_stop = stop

    sending_tasks = []
    if prompt_to_start and node.state == model.State.Stopped:
        node.state = model.State.Starting
        sending_tasks.append(asyncio.create_task(
            node.set_state(model.State.Running, float(prompt_to_start), configuration['node']['time']['starting'])))
    elif prompt_to_stop and node.state == model.State.Running:
        sending_tasks.append(asyncio.create_task(
            node.set_state(model.State.Stopped, transition_time=configuration['node']['time']['starting'])))
    else:
        raise HTTPException(status_code=400, detail="Combination of current state and transition state is not allowed!")
    await asyncio.gather(*sending_tasks)
    return node.state


@app.post(configuration['URL']['notification'])
async def notify(notification: Optional[Notification] = None, state: Optional[str] = None,
                 sender: Optional[str] = None, time_stamp: Optional[float] = 0) -> None:
    """
    Child current state notification that is recursively propagating to the root and updating states on the way

    :param notification: object containing validated state and sender
    :param state: state of the child that sent notification
    :param sender: child's address
    :param time_stamp: time when notification was created
    :return: None
    """
    if configuration['REST']['pydantic']:
        received_state = notification.state
        received_from = notification.sender
    else:
        received_state = state
        received_from = sender

    state_changed = False
    if received_state:
        node.children[int(received_from.split(':')[-1])] = (model.State[received_state.split('.')[-1]], time_stamp)
        state_changed = node.update_state()
    if node.get_parent().address is None:
        return
    if state_changed:
        await post_notification(node.get_parent().get_full_address(), str(node.state), node.address.get_full_address())


def run(created_node: Node, shutdown: Callable) -> None:
    """
    Enable API

    :param shutdown: proper shutdown function
    :param created_node: node instance that is serviced by the API
    :return: None
    """
    global node, shutdown_handler
    node = created_node
    shutdown_handler = shutdown
    log_level = 'critical'
    if configuration['debug']:
        log_level = 'debug'
    uvicorn.run(app, host=configuration['URL']['address'], port=int(node.address.get_port()), log_level=log_level)
