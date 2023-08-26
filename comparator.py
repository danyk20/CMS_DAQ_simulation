import json
import os
import threading
import time

import requests

import model
import send
import utils
from rpc_client import StateRpcClient

configuration: dict[str, str | dict[str, int | str | dict]] = utils.get_configuration()

NODE_ROUTING_KEY = '2.0.0.0.0'
NODE_PORT = '20000'


def measurement_runner(depth: int, children: int):
    """
    Start service int the background

    :param depth: number of levels in the tree
    :param children: number of children per node
    :return: None
    """
    os.system('python service.py --levels ' + str(depth) + ' --children ' + str(children))


def wait_until_node_is_ready(architecture: str) -> None:
    """
    Busy wait until node tree structure is ready

    :param architecture: MOM or REST
    :return: None
    """
    if architecture == 'REST':
        code = 0
        state = 'State.Initialisation'
        while code != 200 or state != 'State.Stopped':
            try:
                url = 'http://127.0.0.1:' + NODE_PORT + configuration['URL']['get_state']
                response = requests.get(url)
                code = response.status_code
                data = json.loads(response.content)
                state = data['State']
            except requests.exceptions.ConnectionError:
                print("Not initialised yet!")
                time.sleep(1)
    else:
        state = 'Initialisation'
        while state != 'Stopped':
            get_state = StateRpcClient()
            print(" [->] Requesting state from node " + NODE_ROUTING_KEY)
            response = get_state.call(NODE_ROUTING_KEY)
            print(" [<-] Received %s" % response)
            if response:
                state = response['state']


def start_root(architecture: str, depth: int, children: int) -> None:
    """
    Send change state to the tree root.

    :param architecture: MOM or REST
    :param depth: number of levels in the tree
    :param children: number of children per node
    :return: None
    """
    print("\n Staring " + architecture + ' with ' + str(children) + ' children and ' + str(depth) + ' levels!')
    wait_until_node_is_ready(architecture)

    if architecture == 'REST':
        url = 'http://127.0.0.1:' + NODE_PORT + configuration['URL']['change_state']
        params = {'start': str(0)}
        response = requests.post(url, json=params)
        if response.status_code != 200:
            print("Root didn't accept the request!")
    else:
        send.open_chanel()
        send.post_state_change(str(model.State.Running), NODE_ROUTING_KEY, 0)


def measurement() -> None:
    """
    Perform all possible combination of the measurement and store it into directory 'Measurements' with path /children/depth

    :return: None
    """
    utils.set_configuration(True, ['measurement', 'write'])
    original_timeout = utils.set_configuration(3, ['rabbitmq', 'rpc_timeout'])
    original_starting = utils.set_configuration(0, ['node', 'time', 'starting'])
    original_get = utils.set_configuration(0, ['node', 'time', 'get'])
    for children in range(1, configuration['measurement']['tree']['children'] + 1):
        for depth in range(1, configuration['measurement']['tree']['depth'] + 1):
            for i in range(configuration['measurement']['runs']):
                original_architecture = utils.set_configuration('MOM', ['architecture'])
                for architecture in configuration['measurement']['architecture']:
                    utils.set_configuration(architecture, ['architecture'])
                    client = threading.Thread(target=lambda: start_root(architecture, depth, children))
                    client.start()
                    measurement_runner(depth, children)
                    client.join()
                utils.set_configuration(original_architecture, ['architecture'])
    utils.set_configuration(False, ['measurement', 'write'])
    utils.set_configuration(original_timeout, ['rabbitmq', 'rpc_timeout'])
    utils.set_configuration(original_starting, ['node', 'time', 'starting'])
    utils.set_configuration(original_get, ['node', 'time', 'get'])


def collect_data(children, depth) -> dict:
    """
    Collect all stored data from 'Measurements' with path /children/depth

    :param children:
    :param depth:
    :return: dictionary with keys MOM and REST and all data collected from Measurements [children][depth]
    """
    rest_data = []
    mom_data = []
    for architecture in ['REST', 'MOM']:
        for i in range(1, children + 1):
            if 'REST' == architecture:
                rest_data.append([])
            else:
                mom_data.append([])
            for j in range(1, depth + 1):
                time_sum = 0
                data = get_node_data(NODE_PORT, i, j, architecture)
                for element in data:
                    time_sum += element
                avg = time_sum / len(data)
                print(architecture + " with " + str(i) + ' children ' + ' and ' + str(j) + ' depth ' + ' took ' + str(
                    avg) + 's')
                if 'REST' == architecture:
                    rest_data[i - 1].append(avg)
                else:
                    mom_data[i - 1].append(avg)
    return {'REST': rest_data, 'MOM': mom_data}


def plot_data(children, depth, architecture) -> None:
    """
    Plot data from list [children][depth]

    :param children: max number of children
    :param depth: max depth
    :param architecture: REST or MOM
    :return: None
    """
    data = collect_data(children, depth)
    selected_data = data[architecture]
    import matplotlib.pyplot as plt

    # Sample nested list containing data
    data_list = selected_data

    # Assuming each inner list has the same length
    x_values = list(range(1, 1 + len(data_list[0])))  # Assuming x-axis values are indices

    # Create a figure and axis
    fig, ax = plt.subplots()

    # Loop through the data sets and plot them
    for i, data_set in enumerate(data_list):
        ax.plot(x_values, data_set, label=f'Children {i + 1}')

    # Add labels and title
    ax.set_xlabel('X-axis')
    ax.set_ylabel('Time [s]')
    ax.set_title('Plot of tree initialisation using ' + architecture)
    ax.legend()

    # Show the plot
    plt.show()


def get_node_data(port, children, depth, architecture) -> list:
    """
    Get data stored in the file about particular node in tree hierarchy

    :param port: node port
    :param children: number of children per node
    :param depth: depth of the ree
    :param architecture: MOM or REST
    :return: list of roundtrip duration from root to the leaves
    """
    result = []
    file_name = architecture + '_duration.txt'
    path = os.path.join('.', 'measurements', str(children),
                        str(depth))
    try:
        f = open(os.path.join(path, file_name), "r")
        line = f.readline()
        while len(line):
            if line.split()[0] == port:
                result.append(float(line.split()[1]))
            line = f.readline()
    except FileNotFoundError:
        return [0] * depth
    return result


measurement()

# for architecture_type in configuration['measurement']['architecture']:
#     plot_data(configuration['measurement']['tree']['children'], configuration['measurement']['tree']['depth'],
#               architecture_type)
