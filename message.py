from typing import Optional

import pydantic

from utils import get_configuration

configuration: dict[str, str | dict[str, str | dict]] = get_configuration()


class ChangeState(pydantic.BaseModel):
    start: Optional[str]
    stop: Optional[str]

    @pydantic.root_validator(pre=True)
    @classmethod
    def start_or_stop(cls, values):
        if 'start' in values and 'stop' in values:
            raise Exception('Start and Stop at the same time!')
        if 'start' not in values and 'stop' not in values:
            raise Exception('Start neither Stop is defined!')
        return values

    @pydantic.validator("start")
    @classmethod
    def start_valid(cls, value):
        probability = float(value)
        if probability < 0 or probability > 1:
            raise Exception('Invalid probability of Start state: ' + value)
        return value

    @pydantic.validator("stop")
    @classmethod
    def stop_valid(cls, value):
        if value != '_':
            raise Exception('Invalid attribute of Stop state: ' + value)
        return value


class Notification(pydantic.BaseModel):
    state: str
    sender: str

    @pydantic.validator("state")
    @classmethod
    def state_valid(cls, value):
        if value.split('.')[-1] not in ['Initialisation', 'Stopped', 'Starting', 'Running', 'Error']:
            raise Exception('Invalid state in Notification: ' + value)
        return value

    @pydantic.validator("sender")
    @classmethod
    def sender_valid(cls, value):
        port = int(value.split(':')[-1])
        if configuration['node']['port']['min'] > port > configuration['node']['port']['max']:
            raise Exception('Invalid sender port in Notification: ' + value)
        return value
