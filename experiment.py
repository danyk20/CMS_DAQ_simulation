from utils import set_message_format, get_white_envelope
from sys import getsizeof

original_format = set_message_format('json')
white_json = get_white_envelope()
set_message_format(original_format)

original_format = set_message_format('proto')
white_proto = get_white_envelope()
set_message_format(original_format)

print(getsizeof(white_json))

print(getsizeof(white_proto))
