from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from testconfig import config
import random


class ContManager:
    def __init__(self, parent, service_name=None):
        self.container_template = 'github.com/threefoldtech/0-templates/container/0.0.1'
        self._parent = parent
        self.logger = self._parent.logger
        self.robot = self._parent.remote_robot
        self._container_service = None
        if service_name:
            try:
                self._container_service = self.robot.service.get(name=service_name)
            except ServiceNotFoundError as e :
                print(e.exception.args[0])
                raise

    @property
    def service(self):
        if self._container_service == None:
            self.logger.error('- container_service is None, Install it first.')
        else:
            return self._container_service

    @property
    def install_state(self):
        return self.service.state.check('actions', 'install', 'ok')

    def install(self, wait=True, **kwargs):
        self.data = {
                'nics': [{'type': 'default', 'name': 'defaultnic'}],
                'flist': "https://hub.grid.tf/tf-bootable/ubuntu:16.04.flist",
                'storage': "zdb://hub.grid.tf:9900",
                'mounts':[],
                'initProcesses':[],
                'hostNetwprking': False,
                'hostname':self._parent.random_string(),
                'ports': [],
                'zerotierNetwork':'',
                'privileged':False,
                'env':[]
                }
        if kwargs:
            self.data.update(kwargs)

        self.container_service_name = "container_{}".format(self._parent.random_string())
        self.logger.info('Install {} container'.format(self.container_service_name))
        self._container_service = self.robot.services.create(self.container_template, self.container_service_name, self.data)
        self._container_service.schedule_action('install').wait(die=wait)

    def uninstall(self, wait=True):
        self.logger.info('Uninstall {} conatiner'.format(self.container_service_name))
        self.service.schedule_action('uninstall').wait(die=wait)

    def start(self):
        return self.service.schedule_action('start').wait(die=True)

    def stop(self):
        return self.service.schedule_action('stop').wait(die=True)

    def add_nic(self, nic):
        return self.service.schedule_action('add_nic', args={'nic': nic}).wait(die=True)

    def remove_nic(self, name):
        return self.service.schedule_action('remove_nic', args={'name': name}).wait(die=True)