from jumpscale import j
from uuid import uuid4
from tests.controller.templates_manager import vm, container

logger = j.logger.get('controller.log')


class Controller:
    def __init__(self, config, god_token=None):
        self.logger = logger
        self.config = config
        if god_token:
            j.clients.zrobot.get(self.config['robot']['client'], data={'url': config['robot']['url'],
                                                                       'god_token_': god_token})
        else:
            j.clients.zrobot.get(self.config['robot']['client'], data={'url': config['robot']['url']})

        self.robot = j.clients.zrobot.robots[self.config['robot']['client']]

        # get instance from all templates_manager
        self.vm_manager = vm.VMManager(parent=self, service_name=None)




    def _generate_random_string(self):
        return str(uuid4()).replace('-', '')[10:]
