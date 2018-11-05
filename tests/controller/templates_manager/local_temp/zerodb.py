from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from testconfig import config
import random


class ZDBManager:
    def __init__(self, parent, service_name=None):
        self.zdb_template = 'github.com/threefoldtech/0-templates/zerodb/0.0.1'
        self._parent = parent
        self.logger = self._parent.logger
        self.robot = self._parent.remote_robot
        self._zdb_service = service_name
        if service_name:
            self._zdb_service = self.robot.service.get(name=service_name)
         
    @property
    def service(self):
        if self._zdb_service == None:
            self.logger.error('ZDB_service is None, Install it first.')
        else:
            return self._zdb_service

    def install(self, path, wait=True, **kwargs):
        default_data = {
            'name' : self._parent._generate_random_string(),
            'sync': True,
            'mode': 'user',
            'admin': self._parent._generate_random_string(),
            'path': path
        }
        if kwargs:
            default_data.update(kwargs)

        self.zdb_service_name = default_data['name']
        self._zdb_service = self.robot.services.create(self.zdb_template, self.zdb_service_name, default_data)
        self._zdb_service.schedule_action('install').wait(die=wait)

    def info(self):
        return self.service.schedule_action('info').wait()
    
    def start(self):
        return self.service.schedule_action('start')

    def stop(self):
        return self.service.schedule_action('stop')

    def namespace_create(self, data):
        return self.service.schedule_action('namespace_create', args=data)

    def namespace_info(self, name):
        return self.service.schedule_action('namespace_info', args={'name': name})

    def namespace_list(self):
        return self.service.schedule_action('namespace_list')

    def namespace_set(self, data):
        return self.service.schedule_action('namespace_set', args=data)

    def namespace_url(self):
        return self.service.schedule_action('namespace_url')

    def namespace_private_url(self):
        return self.service.schedule_action('namespace_private_url')

    def namespace_delete(self, name):
        return self.service.schedule_action('namespace_delete', args={'name': name})