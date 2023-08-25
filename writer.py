import os
import signal


def add_measurement(file_name, node, duration, children, depth):
    path = os.path.join('.', 'measurements', str(children),
                        str(depth))
    if not os.path.exists(path):
        os.makedirs(path)
    try:
        f = open(os.path.join(path, file_name), "a")
        line = node + ' ' + str(duration) + os.linesep
        f.write(line)
        f.close()
    except Exception as e:
        print(e)
    os.kill(os.getpid(), signal.SIGTERM)
