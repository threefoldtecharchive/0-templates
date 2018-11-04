from jumpscale import j
from uuid import uuid4
from tests.controller.templates_manager.local_temp import vm, container, zerodb

logger = j.logger.get('controller.log')


class Controller:
    def __init__(self, config, god_token=None):
        self.logger = logger
        self.config = config
        # local remote
        if god_token:
            j.clients.zrobot.get(self.config['robot']['client'], data={'url': config['robot']['server'],
                                                                       'god_token_': god_token})
        else:
            j.clients.zrobot.get(self.config['robot']['client'], data={'url': config['robot']['server']})

        self.robot = j.clients.zrobot.robots[self.config['robot']['client']]

        # remote robot
        j.clients.zrobot.get(self.config['robot']['remote_client'], data={'url': config['robot']['remote_server']})
        self.remote_robot = j.clients.zrobot.robots[self.config['robot']['remote_client']]
        self.node = j.clients.zos.get('remote_node', data={'host':self.config['robot']['remote_server'][7:-5]})

        # get instance from all templates_manager
        self.vm_manager = vm.VMManager(parent=self, service_name=None)
        self.zdb_manager = zerodb.ZDBManager(parent=self, service_name=None)
        self.container_manager = container.ContManager(parent=self, service_name=None)
        
    def _generate_random_string(self):
        return str(uuid4()).replace('-', '')[10:]