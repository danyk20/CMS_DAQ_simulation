import json
import time

import numpy as np

from model import State
from utils import set_message_format, get_white_envelope, get_orange_envelope, get_red_envelope, get_blue_envelope
from sys import getsizeof
import matplotlib.pyplot as plt
import experiment_pb2

SENTENCE = "CERN, the European Organization for Nuclear Research, is one of the world's largest and most respected " \
           "centres for scientific research."


def get_list(length: int):
    """
    Generate list of string with selected number of elements

    :param length: number of elements
    :return: list
    """
    words = SENTENCE.split()
    index = 0
    result = []
    for i in range(length):
        if index == len(words):
            index = 0
        result.append(words[index])
        index += 1
    return result


def get_dict(length: int, long_key: bool = False):
    """
    Generate dictionary of string, string with selected number of elements

    :param long_key: boolean value whether to use long key
    :param length: number of elements
    :return: list
    """
    words = SENTENCE.split()
    index = 0
    result = dict()
    for i in range(length):
        key = str(i) + SENTENCE if long_key else str(i)
        if index == len(words):
            index = 0
        result[key] = words[index]
        index += 1
    return result


def get_proto_array(array: list):
    """
    Convert list of Strings to list Protocol Buffer

    :param array: input
    :return: Protocol Buffer Object
    """
    result = experiment_pb2.Array()
    result.word.extend(array)
    return result


def get_proto_dictionary(data: dict):
    """
    Convert list of Strings to list Protocol Buffer

    :param data: input
    :return: Protocol Buffer Object
    """
    result = experiment_pb2.Dictionary()
    result.data.update(data)
    return result


def get_avg_size(envelope_list: list, raw_type):
    """
    Compute average size of envelope in the list

    :param envelope_list: input list
    :param raw_type: is it non serialised Protocol Buffer object
    :return: average size in Bytes
    """
    size = 0
    for envelope in envelope_list:
        if raw_type:  # raw Protocol Buffer
            size += envelope.ByteSize()
        else:
            size += getsizeof(envelope)
    return size / len(envelope_list)


def generate_envelopes():
    """
    Generate all possible envelopes

    :return: Dictionary with all valid envelopes
    """
    white = [get_white_envelope()]
    blue = []
    red = []
    orange = []
    for state in State:
        blue.append(get_blue_envelope(str(state)))
        red.append(get_red_envelope(str(state), '2.3.4.5.6'))
        orange.append(get_orange_envelope(str(state), 0.123456))
    return {'white': white, 'blue': blue, 'red': red, 'orange': orange}


def measure_envelopes(json_envelopes, proto_envelopes, plot_name):
    """
    Measure size and plot lists (json & proto)

    :param json_envelopes: all envelopes as dictionary encoded in json
    :param proto_envelopes: all envelopes as dictionary encoded in Protocol Buffer
    :param plot_name: image name
    :return: None
    """
    x_ax = [1, 2, 3, 4, 5, 6, 7, 8]

    json_size = dict(map(lambda x: (x[0], get_avg_size(x[1], False)), json_envelopes.items()))
    proto_size = dict(map(lambda x: (x[0], get_avg_size(x[1], False)), proto_envelopes.items()))

    # heights of bars
    size = [json_size['white'], proto_size['white'], json_size['blue'], proto_size['blue'], json_size['red'],
            proto_size['red'], json_size['orange'],
            proto_size['orange']]

    # labels for bars
    tick_label = ['white json', 'white proto', 'blue json', 'blue proto', 'red json', 'red proto', 'orange json',
                  'orange proto']

    plot_graph(plot_name, size, tick_label, x_ax)


def measure_size(json_data: list, proto_data: list, plot_name: str):
    """
    Measure size and plot lists (json & proto)

    :param json_data: input list encoded in json
    :param proto_data: input list encoded in Protocol Buffer
    :param plot_name: image name
    :return: None
    """

    json_size = list(map(lambda x: getsizeof(x), json_data))
    proto_size = list(map(lambda x: getsizeof(x.SerializeToString()), proto_data))
    proto_raw_size = list(map(lambda x: x.ByteSize(), proto_data))

    size = []  # heights of bars
    for i in range(len(json_data)):
        size.append(json_size[i])
        size.append(proto_size[i])
        size.append(proto_raw_size[i])

    # labels for bars
    tick_label = []
    for element in json_data:
        tick_label.append(str(len(json.loads(element))))
        tick_label.append(str(len(json.loads(element))))
        tick_label.append(str(len(json.loads(element))))

    plot_grouped_graph(json_size, proto_size, proto_raw_size, plot_name, 'Size (B)', 'List as JSON vs Protocol Buffer')


def plot_grouped_graph(json_val, proto_val, proto_raw_val, plot_name, y_label, title):
    """
    Plot and save grouped bar graph

    :param title: plot title
    :param y_label: label on y axes
    :param json_val: 1st bar in the group
    :param proto_val: 2nd bar in the group
    :param proto_raw_val: 3rd bar in the group
    :param plot_name: image name
    :return: None
    """
    species = ('10', '100', '1k', '10k', '100k', '1M')
    measurements = {
        'JSON': tuple(json_val),
        'Protocol Buffer serialised': tuple(proto_val),
        'Protocol Buffer raw': tuple(proto_raw_val),
    }
    colors = {'JSON': 'red', 'Protocol Buffer serialised': 'blue', 'Protocol Buffer raw': 'green', }

    x = np.arange(len(species))  # the label locations
    width = 0.25  # the width of the bars
    multiplier = 0

    fig, ax = plt.subplots(layout='constrained')

    for attribute, measurement in measurements.items():
        offset = width * multiplier
        ax.bar(x + offset, measurement, width, label=attribute, color=colors[attribute])
        multiplier += 1

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_ylabel(y_label)
    ax.set_xlabel('number of elements in the list')
    ax.set_title(title)
    ax.set_xticks(x + width, species)
    ax.legend(loc='upper left')
    ax.set_yscale('log')

    plt.savefig('resources/' + plot_name + '.png')
    plt.show()


def plot_graph(plot_name: str, values: list, tick_label: list, x_ax: list) -> None:
    """
    Plot and save bar graph

    :param plot_name: image name
    :param values: measured values
    :param tick_label: labels
    :param x_ax: position of labels
    :return: None
    """
    # plotting a bar chart
    plt.bar(x_ax, values, tick_label=tick_label,
            width=0.8, color=['red', 'blue'])
    # rotate labels
    plt.xticks(rotation=35)
    colors = {'JSON': 'red', 'Protocol Buffer': 'blue'}
    labels = list(colors.keys())
    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[label]) for label in labels]
    plt.legend(handles, labels)
    # naming the x-axis
    plt.xlabel('envelope type')
    # naming the y-axis
    plt.ylabel('size in bytes')
    # plot title
    plt.title('Comparison of JSON vs Protocol Buffer on all envelopes!')
    # add extra space for labels
    plt.subplots_adjust(bottom=0.15)
    # function to show the plot
    plt.savefig('resources/' + plot_name + '.png')
    plt.show()


def compute_avg_list(aggregated_list) -> list:
    result = [0] * len(aggregated_list[0])
    for measurement in aggregated_list:
        for i in range(len(measurement)):
            result[i] += measurement[i]
    result = list(map(lambda x: x / len(aggregated_list), result))
    return result


def list_generator(measurements: int = 1):
    """
    Generate list of string with following number of elements [10, 100, 1000, 10000, 100000, 1000000]

    :return: tuple where the first element is encoded in json and the other in Protocol Buffer
    """
    sizes = [10, 100, 1000, 10000, 100000, 1000000]
    inputs = []
    for size in sizes:
        inputs.append(get_list(size))
    json_val = []
    proto_val = []
    aggregated_time_json = []
    aggregated_time_proto = []
    aggregated_time_proto_raw = []
    for _ in range(measurements):
        json_val = []
        proto_val = []
        json_duration = []
        proto_raw_duration = []
        proto_duration = []
        for element in inputs:
            start = time.time()
            json_val.append(json.dumps(element))
            json_duration.append(time.time() - start)

            start = time.time()
            proto_val.append(get_proto_array(element))
            proto_raw_duration.append(time.time() - start)
            start = time.time()
            proto_val[-1].SerializeToString()
            proto_duration.append(time.time() - start + proto_raw_duration[-1])
        aggregated_time_json.append(json_duration)
        aggregated_time_proto.append(proto_duration)
        aggregated_time_proto_raw.append(proto_raw_duration)

    json_duration = compute_avg_list(aggregated_time_json)
    proto_duration = compute_avg_list(aggregated_time_proto)
    proto_raw_duration = compute_avg_list(aggregated_time_proto_raw)

    return json_val, proto_val, json_duration, proto_duration, proto_raw_duration


def dict_generator(long_key: bool = False, measurements: int = 1):
    """
    Generate dict of string with following number of elements [10, 100, 1000, 10000, 100000, 1000000]

    :return: tuple where the first element is encoded in json and the other in Protocol Buffer
    """
    sizes = [10, 100, 1000, 10000, 100000, 1000000]
    inputs = []
    for size in sizes:
        inputs.append(get_dict(size, long_key))
    json_val = []
    proto_val = []
    aggregated_time_json = []
    aggregated_time_proto = []
    aggregated_time_proto_raw = []
    for i in range(measurements):
        json_val = []
        proto_val = []
        json_duration = []
        proto_raw_duration = []
        proto_duration = []
        for element in inputs:
            start = time.time()
            json_val.append(json.dumps(element))
            json_duration.append(time.time() - start)

            start = time.time()
            proto_val.append(get_proto_dictionary(element))
            proto_raw_duration.append(time.time() - start)
            start = time.time()
            proto_val[-1].SerializeToString()
            proto_duration.append(time.time() - start + proto_raw_duration[-1])
        aggregated_time_json.append(json_duration)
        aggregated_time_proto.append(proto_duration)
        aggregated_time_proto_raw.append(proto_raw_duration)

    json_duration = compute_avg_list(aggregated_time_json)
    proto_duration = compute_avg_list(aggregated_time_proto)
    proto_raw_duration = compute_avg_list(aggregated_time_proto_raw)

    return json_val, proto_val, json_duration, proto_duration, proto_raw_duration


original_format = set_message_format('json')
envelopes_json = generate_envelopes()
set_message_format(original_format)

original_format = set_message_format('proto')
envelopes_proto = generate_envelopes()
set_message_format(original_format)

measure_envelopes(envelopes_json, envelopes_proto, 'envelopes_json_vs_proto')

json_list, proto_list, json_time, proto_time, proto_raw_time = list_generator(100)
measure_size(json_list, proto_list, 'list_json_vs_proto')
plot_grouped_graph(json_time, proto_time, proto_raw_time, 'time_list_json_vs_proto', 'time [s]',
                   'Duration of converting list into JSON vs Protocol Buffer')

json_dict, proto_dict, json_dict_time, proto_dict_time, proto_dict_raw_time = dict_generator(True, 100)
measure_size(json_dict, proto_dict, 'dict_json_vs_proto')
plot_grouped_graph(json_dict_time, proto_dict_time, proto_dict_raw_time, 'time_dict_json_vs_proto', 'time [s]',
                   'Duration of converting dictionary into JSON vs Protocol Buffer')

json_dict, proto_dict, json_dict_time, proto_dict_time, proto_dict_raw_time = dict_generator(False, 100)
measure_size(json_dict, proto_dict, 'dict_short_json_vs_proto')
plot_grouped_graph(json_dict_time, proto_dict_time, proto_dict_raw_time, 'time_dict_short_json_vs_proto', 'time [s]',
                   'Duration of converting dictionary into JSON vs Protocol Buffer')
