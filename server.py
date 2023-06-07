import time
from typing import Union

import uvicorn
from fastapi import FastAPI

import model
from model import Node

node: Node | None = None
app = FastAPI()
IP_ADDRESS = '127.0.0.1'


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.get("/statemachine/state")
def get_state() -> dict[str, str]:
    return {"State": str(node.state)}


@app.post("/statemachine/input")
async def change_state(Start: str = None, Stop: str = None):
    if Start:
        node.state = model.State.Starting
        time.sleep(10)
        node.state = model.State.Running
    elif Stop:
        node.state = model.State.Stopped
    pass


@app.post("/notifications")
def notify():
    pass


def run(created_node: Node):
    global node
    node = created_node
    uvicorn.run(app, host=IP_ADDRESS, port=int(node.address.get_port()))


