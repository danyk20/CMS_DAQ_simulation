# Introduction

This script create tree hierarchy of nodes where each node is running as separate process with public REST API.

## API

### GET /statemachine/state
- return current state of the node as one of the following:
  - "State": "State.Stopped"
  - "State": "State.Starting"
  - "State": "State.Running"
  - "State": "State.Error"
- synchronous operation
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
- asynchronous operation using asyncio
  - start=x
    1. immediately change state from State.Stopped to State.Starting
    2. `await` sleep 10 s
    3. propagate this request to all its children if any by creating tasks
    4. `await` for all task
    5. set own state based on x probability and children states
  - stop=y
    1. propagate immediately this request to all its children if any
    2. stop itself
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
- asynchronous operation using asyncio
  - 'await' posting notification to its parent if not root

## Client
This script contains manually created client however it is possible to generate client automatically for following languages:
  -C++
  -C#
  -Java
  -PHP
  -Python
  -Ruby
  -Scala

### Autogenerate python client
```sh
pipenv install
pipenv run openapi-python-client generate --url http://127.0.0.1:20000/openapi.json
```
NOTE: You might have to change IP and port ich you have changed `configuration.yaml` file!

Or use web generator https://editor.swagger.io/ where you just upload http://127.0.0.1:20000/openapi.json (much straightforward usage than offline generator because of good `README.md` containing personalised example).

After execution of commands above, you should be able to see a new directory with generated client library.

# Prerequisite

Pipenv - https://pypi.org/project/pipenv/

# Run 

```sh
pipenv install
pipenv run python service.py --port 20000 --levels 2 --children 3
```

# Configuration

There is `configuration.yaml` file containing all variables that are possible to change.

# Description

After running there will be created tree hierarchy of nodes where each of them exposes REST API described above. Originally all nodes are in `State.Stopped` after initialization what can be verified by `GET` request to `/statemachine/state` endpoint. It's possible to sent `POST` request to `/statemachine/input endpoint` in order to change the state. There are two possible parameters `start` and `stop`. `start` parameter define probability of going into `State.Error` and it must be in range [0,1]. Node change state to `State.Starting` immediately after submitting the request and remains in that state until all it children change state as well. There are 2 possible scenarios: either all children nodes and also current node successfully transitioned into `State.Running` or at least one node (doesn't matter weather current or child) transitioned into `State.Error` - then current node's state is `State.Error`. Running node can transition into `State.Error` with probability defined in the start parameter and this process is periodically repeated with period defined in the `configuration.yaml` file. 

`/notofications` endpoint is called automatically when node changes its state from `State.Running` to `State.Error` or `State.Stopped`. This way parent can be immediately updated about the change of children and also update its state as well and propagate this information to its parent until the root node is informed. 

## State Diagram

![State Diagram](resources%2Fstate_diagram.png)

### Legend:
- x = chance to fail - entered parameter while sending POST request to the endpoint
- w = node.time.starting from `configuration.yaml`
- y = randomly generated value from range (0,1)
- z = node.time.running from `configuration.yaml`

# Shutdown

Sending signal SIGTERM `kill -15 <PID>` will be propagated from node to all its children. Node waits for termination of its children and terminate itself after all children are terminated or after 20 s since SIGTERM signal arrived (what is earlier). 