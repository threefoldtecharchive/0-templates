from Jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from testconfig import config
import random


class NodeManager:
    def __init__(self, parent):
        self.node_template = 'github.com/threefoldtech/0-templates/node/0.0.1'
        self._parent = parent
        self.logger = self._parent.logger
        self.robot = self._parent.remote_robot
        self._node_service = None

    @property
    def service(self):
        if self._node_service is None:
            self._node_service = self.robot.services.find(template_name='node')[0]
        return self._node_service

    def reboot(self):
        return self.service.schedule_action('reboot').wait(die=True)

    def info(self):
        return self.service.schedule_action('info').wait(die=True)

    def stats(self):
        return self.service.schedule_action('stats').wait(die=True)

    def processes(self):
        return self.service.schedule_action('processes').wait(die=True)

    def os_version(self):
        return self.service.schedule_action('os_version').wait(die=True)

    def create_zdb_namespace(self):
        args = {
            'disktype': 'hdd',
            'mode': 'user',
            'password': self._parent.random_string(),
            'public': False,
            'ns_size': random.randint(1, 20),
            'name': self._parent.random_string()
        }
        return self.service.schedule_action('create_zdb_namespace', args).wait(die=True)
