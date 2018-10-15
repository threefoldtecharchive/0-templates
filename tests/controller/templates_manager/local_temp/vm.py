from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from testconfig import config
import random

class VMManager:
    def __init__(self, parent, service_name=None):
        self.vm_template = 'github.com/threefoldtech/0-templates/vm/0.0.1'
        self._parent = parent
        self.logger = self._parent.logger
        self.robot = self._parent.remote_robot

        if service_name:
            try:
                self._vm_service = self.robot.service.get(name=service_name)
            except ServiceNotFoundError:
                self._vm_service = None
        else:
            self._vm_service = None

    @property
    def service(self):
        if self._vm_service == None:
            self.logger.error('- VM_service is None, Install it first.')
        else:
            return self._vm_service

    @property
    def install_state(self):
        return self.service.state.check('actions', 'install', 'ok')

    def install(self, wait=True, **kwargs):
        ssh_port = random.randint(22022, 22922)
        default_data = {
            'memory': 2048,
            'cpu': 1,
            'nics': [{'type': 'default', 'name': 'defaultnic'}],
            'flist': 'https://hub.grid.tf/tf-bootable/ubuntu:latest.flist',
            'ports': [{'source': ssh_port, 'target': 22, 'name': 'ssh'}],
            'configs': [
                {'path': '/root/.ssh/authorized_keys', 'content': config['vm']['ssh'],
                 'name': 'sshkey'}]
        }
        if kwargs:
            default_data.update(kwargs)

        self.vm_service_name = "vm_{}".format(self._parent._generate_random_string())
        self.logger.info('Install {} vm, ssh port : {} '.format(self.vm_service_name, ssh_port))
        self._vm_service = self.robot.services.create(self.vm_template, self.vm_service_name, default_data)
        self._vm_service.schedule_action('install').wait(die=wait)

    def uninstall(self, wait=True):
        self.logger.info('Uninstall {} vm'.format(self.vm_service_name))
        self.service.schedule_action('uninstall').wait(die=wait)

    def info(self):
        return self.service.schedule_action('info')

