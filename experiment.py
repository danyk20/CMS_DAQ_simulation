from model import State
from utils import set_message_format, get_white_envelope, get_orange_envelope, get_red_envelope, get_blue_envelope
from sys import getsizeof
import matplotlib.pyplot as plt


def get_avg_size(envelope_list: list):
    size = 0
    for envelope in envelope_list:
        size += getsizeof(envelope)
    return size / len(envelope_list)


def generate_envelopes():
    white = [get_white_envelope()]
    blue = []
    red = []
    orange = []
    for state in State:
        blue.append(get_blue_envelope(str(state)))
        red.append(get_red_envelope(str(state), '2.3.4.5.6'))
        orange.append(get_orange_envelope(str(state), 0.123456))
    return {'white': white, 'blue': blue, 'red': red, 'orange': orange}


def plot_results(json, proto):# x-coordinates of left sides of bars
    left = [1, 2, 3, 4, 5, 6, 7, 8]

    json_size = dict(map(lambda x: (x[0], get_avg_size(x[1])), json.items()))
    proto_size = dict(map(lambda x: (x[0], get_avg_size(x[1])), proto.items()))

    # heights of bars
    size = [json_size['white'], proto_size['white'], json_size['blue'], proto_size['blue'], json_size['red'],
            proto_size['red'], json_size['orange'],
            proto_size['orange']]

    # labels for bars
    tick_label = ['white json', 'white proto', 'blue json', 'blue proto', 'red json', 'red proto', 'orange json',
                  'orange proto']

    # plotting a bar chart
    plt.bar(left, size, tick_label=tick_label,
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
    plt.savefig('resources/json_vs_proto.png')
    plt.show()


original_format = set_message_format('json')
envelopes_json = generate_envelopes()
set_message_format(original_format)

original_format = set_message_format('proto')
envelopes_proto = generate_envelopes()
set_message_format(original_format)

plot_results(envelopes_json, envelopes_proto)
