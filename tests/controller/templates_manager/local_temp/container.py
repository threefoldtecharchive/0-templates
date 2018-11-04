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

    def install(self,data, wait=True):
        self.container_service_name = "container_{}".format(self._parent._generate_random_string())
        self.logger.info('Install {} container'.format(self.container_service_name))
        self._container_service = self.robot.services.create(self.container_template, self.container_service_name, data)
        self._container_service.schedule_action('install').wait(die=wait)

    def uninstall(self, wait=True):
        self.logger.info('Uninstall {} conatiner'.format(self.container_service_name))
        self.service.schedule_action('uninstall').wait(die=wait)

    def start(self):
        return self.service.schedule_action('start')

    def stop(self):
        return self.service.schedule_action('stop')
    