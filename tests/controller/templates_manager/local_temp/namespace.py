from Jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from testconfig import config
import random

class NSManager:
    def __init__(self, parent, service_name=None):
        self.ns_template = 'github.com/threefoldtech/0-templates/namespace/0.0.1'
        self._parent = parent
        self.logger = self._parent.logger
        self.robot = self._parent.remote_robot
        self._ns_service = service_name
        if service_name:
            self._ns_service = self.robot.service.get(name=service_name)
         
    @property
    def service(self):
        if self._ns_service == None:
            self.logger.error('NS_service is None, Install it first.')
        else:
            return self._ns_service

    def install(self, wait=True, **kwargs):
        self.default_data = {
            'size': random.randint(1, 50),
            'nsName' : self._parent._generate_random_string(),
            'diskType': 'hdd',
            'public': False,
            'mode': 'user',
            'password': self._parent._generate_random_string(),
        }
        if kwargs:
            self.default_data.update(kwargs)

        self.ns_service_name = self.default_data['nsName']
        self._ns_service = self.robot.services.create(self.ns_template, self.ns_service_name, self.default_data)
        self._ns_service.schedule_action('install').wait(die=wait)

    def info(self):
        return self.service.schedule_action('info').wait(die=True)
    
    def url(self):
        return self.service.schedule_action('url').wait(die=True)

    def private_url(self):
        return self.service.schedule_action('private_url').wait(die=True)

    def uninstall(self):
        return self.service.schedule_action('uninstall').wait(die=True)

    def connection_info(self):
        return self.service.schedule_action('connection_info').wait(die=True)
