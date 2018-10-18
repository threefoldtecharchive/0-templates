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
        self._vm_service = None
        if service_name:
            try:
                self._vm_service = self.robot.service.get(name=service_name)
            except ServiceNotFoundError:
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

    def install(self, data, wait=True):
        self.vm_service_name = data['name']
        self._vm_service = self.robot.services.create(self.vm_template, self.vm_service_name, data)
        self._vm_service.schedule_action('install').wait(die=wait)

    def uninstall(self, wait=True):
        self.logger.info('Uninstall {} vm'.format(self.vm_service_name))
        self.service.schedule_action('uninstall').wait(die=wait)

    def info(self):
        return self.service.schedule_action('info')

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