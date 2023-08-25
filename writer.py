import os
import signal


def add_measurement(file_path, node, duration):
    try:
        f = open(file_path, "a")
        line = node + ' ' + str(duration) + os.linesep
        f.write(line)
        f.close()
    except Exception as e:
        print(e)
    os.kill(os.getpid(), signal.SIGTERM)
