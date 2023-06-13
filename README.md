# Introduction

This script create tree hierarchy of nodes where each node is running as separate process with public REST API.

## API

### GET /statemachine/state
- return current state of the node as one of the following:
  - "State": "State.Stopped"
  - "State": "State.Starting"
  - "State": "State.Running"
  - "State": "State.Error"
### POST /statemachine/input
- change state of the node
  - from stopped to starting and then running
  - from running immediately to stopped
- 3 parameters;
  - start
    - decimal number between 0 and 1
    - probability of failure
  - stop
    - any nonempty string
  - debug
    - true/false 
    - debug prints containing timestamps when changing state
### POST /notifications
- update parent about current state
- it is propagated from origin to root node 
  - update each node on the way
- parameters:
  - state 
    - current state of the sender
    - filled automatically
  - sender
    - full URL of the sender
    - filled automatically

# Prerequisite

Pipenv - https://pypi.org/project/pipenv/

# Run 

```sh
pipenv install
pipenv run python service.py --port 20000 --levels 2 --children 3
````

# Configuration

There is `configuration.yaml` file containing all variables that are possible to change.