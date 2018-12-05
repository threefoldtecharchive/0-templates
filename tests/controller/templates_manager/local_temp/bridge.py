from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from testconfig import config
import random

class BrigeManager:
    def __init__(self, parent, service_name=None):
        self.bridge_template = 'github.com/threefoldtech/0-templates/bridge/0.0.1'
        self._parent = parent
        self.logger = self._parent.logger
        self.robot = self._parent.remote_robot
        self._bridge_service = None
        if service_name:
            self._bridge_service = self.robot.service.get(name=service_name)
         
    @property
    def service(self):
        if self._bridge_service == None:
            self.logger.error('bridge_service is None, Install it first.')
        else:
            return self._bridge_service

    def install(self, wait=True, **kwargs):
        self.default_data = {
            'name': self._parent.random_string()[:10],
            'hwaddr' : None,
            'mode': 'none',
            'nat': False,
            'settings': {}
        }
        if kwargs:
            self.default_data.update(kwargs)

        self.bridge_service_name = self.default_data['name']
        self._bridge_service = self.robot.services.create(self.bridge_template, self.bridge_service_name, self.default_data)
        self._bridge_service.schedule_action('install').wait(die=wait)

    def uninstall(self):
        return self.service.schedule_action('uninstall').wait(die=True)
    
    def nic_add(self, nic):
        return self.service.schedule_action('nic_add', args={'nic': nic}).wait(die=True)

    def nic_remove(self, nic):
        return self.service.schedule_action('nic_remove', args={'nic': nic}).wait(die=True)

    def nic_list(self):
        return self.service.schedule_action('nic_list').wait(die=True)