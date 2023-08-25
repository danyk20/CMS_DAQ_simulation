import os

import utils

configuration: dict[str, str | dict[str, int | str | dict]] = utils.get_configuration()

for children in range(1, configuration['measurement']['tree']['children'] + 1):
    for depth in range(1, configuration['measurement']['tree']['depth'] + 1):
        for i in range(configuration['measurement']['runs']):
            original_architecture = utils.set_configuration('MOM', ['architecture'])
            for architecture in configuration['measurement']['architecture']:
                utils.set_configuration(architecture, ['architecture'])
                os.system('python service.py --levels ' + str(depth) + ' --children ' + str(children))
            utils.set_configuration(original_architecture, ['architecture'])

