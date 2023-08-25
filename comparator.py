import os

import utils

configuration: dict[str, str | dict[str, int | str | dict]] = utils.get_configuration()

for i in range(configuration['measurement']['runs']):
    original_architecture = utils.set_configuration('MOM', ['architecture'])
    for architecture in configuration['measurement']['architecture']:
        utils.set_configuration(architecture, ['architecture'])
        os.system('python service.py --levels ' + str(configuration['measurement']['tree']['depth']) + ' --children ' +
                  str(configuration['measurement']['tree']['children']))
    utils.set_configuration(original_architecture, ['architecture'])
