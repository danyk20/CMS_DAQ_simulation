import os
import threading
import time

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.tri import Triangulation

import requests

import model
import send
import utils

configuration: dict[str, str | dict[str, int | str | dict]] = utils.get_configuration()


def measurement_runner(depth, children):
    os.system('python service.py --levels ' + str(depth) + ' --children ' + str(children))


def start_root(architecture, depth, children):

    print("\nStaring!")

    if architecture == 'REST':
        code = 0
        while code != 200:
            try:
                url = 'http://127.0.0.1:20000'+ configuration['URL']['change_state']
                params = {'start': str(0)}

                x = requests.post(url, json=params)
                code = x.status_code
            except Exception as e:
                print("failed")
                time.sleep(0.5)


    else:
        time.sleep(2 + depth * 1 * children)
        send.open_chanel()
        send.post_state_change(str(model.State.Running), '2.0.0.0.0', 0)



def measurement():
    utils.set_configuration(True, ['measurement', 'write'])
    for children in range(1, configuration['measurement']['tree']['children'] + 1):
        for depth in range(1, configuration['measurement']['tree']['depth'] + 1):
            for i in range(configuration['measurement']['runs']):
                original_architecture = utils.set_configuration('MOM', ['architecture'])
                for architecture in configuration['measurement']['architecture']:
                    utils.set_configuration(architecture, ['architecture'])
                    # thread1 = threading.Thread(target=lambda: measurement_runner(depth, children))
                    thread2 = threading.Thread(target=lambda: start_root(architecture, depth, children))
                    # thread1.start()
                    thread2.start()
                    measurement_runner(depth, children)
                    # thread1.join()
                    thread2.join()
                utils.set_configuration(original_architecture, ['architecture'])
    utils.set_configuration(False, ['measurement', 'write'])


def collect_data(children, depth):
    rest_data = []
    mom_data = []
    for architecture in ['REST', 'MOM']:
        for i in range(1, children + 1):
            if 'REST' == architecture:
                rest_data.append([])
            else:
                mom_data.append([])
            for j in range(1, depth + 1):
                sum = 0
                data = get_node('20000', i, j, architecture)
                for element in data:
                    sum += element
                avg = sum / len(data)
                print(architecture + " with " + str(i) + ' childrens ' + ' and ' + str(j) + ' depth ' + ' took ' + str(
                    avg) + 's')
                if 'REST' == architecture:
                    rest_data[i - 1].append(avg)
                else:
                    mom_data[i - 1].append(avg)
    return {'REST': rest_data, 'MOM': mom_data}


def plot_data(children, depth, architecture):
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


def get_node(port, children, depth, architecture):
    result = []
    file_name = architecture + '_duration.txt'
    path = os.path.join('.', 'measurements', str(children),
                        str(depth))
    f = open(os.path.join(path, file_name), "r")
    line = f.readline()
    while len(line):
        if line.split()[0] == port:
            result.append(float(line.split()[1]))
        line = f.readline()
    return result


# for architecture in configuration['measurement']['architecture']:
#     plot_data(configuration['measurement']['tree']['children'], configuration['measurement']['tree']['depth'],
#               architecture)
measurement()
