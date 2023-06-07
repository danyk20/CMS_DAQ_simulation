from typing import Union

from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.get("/statemachine/state")
def get_state() -> dict[str, str]:
    return {"State": "MY_STATE"}


@app.post("/statemachine/input")
async def change_state(Start: str = None, Stop: str = None):
    pass


@app.post("/notifications")
def notify():
    pass
