from Jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from testconfig import config
import random

class VMManager:
    def __init__(self, parent, service_name=None):
        self.vm_template = 'github.com/threefoldtech/0-templates/vm/0.0.1'
        self._parent = parent
        self.logger = self._parent.logger
        self.robot = self._parent.remote_robot
        self._vm_service = service_name
        if service_name:
            self._vm_service = self.robot.service.get(name=service_name)


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
        return self.service.schedule_action('info').wait(die=True)

    def shutdown(self, force=True):
        return self.service.schedule_action('shutdown')
    
    def start(self):
        return self.service.schedule_action('start')

    def stop(self):
        return self.service.schedule_action('stop')
    
    def pause(self):
        return self.service.schedule_action('pause')    

    def resume(self):
        return self.service.schedule_action('resume')    

    def reboot(self):
        return self.service.schedule_action('reboot')    

    def reset(self):
        return self.service.schedule_action('reset')    

    def enable_vnc(self):
        return self.service.schedule_action('enable_vnc')    

    def disable_vnc(self):
        return self.service.schedule_action('disable_vnc')
    
    def add_portforward(self, name, source, target):
        if type(source) != int or type(target) != int:
            raise ValueError ('Source and Target type must be int')
        return self.service.schedule_action('add_portforward', args={'name': name, 'source': source, 'target': target})

    def remove_portforward(self, name):
        return self.service.schedule_action('remove_portforward', args={'name': name})
