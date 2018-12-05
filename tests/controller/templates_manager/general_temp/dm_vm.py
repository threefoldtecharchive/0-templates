from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from testconfig import config
import random

class DMVMManager:
    def __init__(self, parent, service_name=None):
        self.dm_vm_template = 'github.com/threefoldtech/0-templates/dm_vm/0.0.1'
        self._parent = parent
        self.logger = self._parent.logger
        self.robot = self._parent.robot
        self._dm_vm_service = None
        if service_name:
            self._dm_vm_service = self.robot.service.get(name=service_name)


    @property
    def service(self):
        if self._dm_vm_service == None:
            self.logger.error('VM_service is None, Install it first.')
        else:
            return self._dm_vm_service

    @property
    def install_state(self):
        return self.service.state.check('actions', 'install', 'ok')

    def install(self, wait=True, **kwargs):
        ssh_port = random.randint(22022, 22922)
        zt_client = self._parent.zt_client(self._parent, local=True)
        default_data = {
            'memory': 2048,
            'cpu': 1,
            'mgmtNic': {'name': self._parent.random_string(),
                        'type': 'zerotier', 'id': config['zt']['zt_netwrok_id'],
                        'ztClient': zt_client.service_name},
            'image': 'ubuntu',
            'nodeId': config['node']['nodeid'],
            'ports': [{'source': ssh_port, 'target': 22, 'name': 'ssh'}],
            'configs': [
                {'path': '/root/.ssh/authorized_keys', 'content': config['vm']['ssh'],
                 'name': 'sshkey'}]
        }
        if kwargs:
            default_data.update(kwargs)

        if default_data['image'] == 'zero-os':
            default_data['kernelArgs'] = [{'name': 'development', 'key': 'development'}]

        self.dm_vm_service_name = "vm_{}".format(self._parent.random_string())
        self.logger.info('Install {} vm, ssh port : {} '.format(self.dm_vm_service_name, ssh_port))
        self._dm_vm_service = self.robot.services.create(self.dm_vm_template, self.dm_vm_service_name, default_data)
        self._dm_vm_service.schedule_action('install').wait(die=wait)

    def uninstall(self, wait=True):
        self.logger.info('Uninstall {} vm'.format(self.dm_vm_service_name))
        self.service.schedule_action('uninstall').wait(die=wait)

    def info(self):
        return self.service.schedule_action('info').wait(die=True)

    def shutdown(self, force=True):
        return self.service.schedule_action('shutdown').wait(die=True)
    
    def start(self):
        return self.service.schedule_action('start').wait(die=True)

    def stop(self):
        return self.service.schedule_action('stop').wait(die=True)
    
    def pause(self):
        return self.service.schedule_action('pause').wait(die=True)

    def resume(self):
        return self.service.schedule_action('resume').wait(die=True)

    def reboot(self):
        return self.service.schedule_action('reboot').wait(die=True)

    def reset(self):
        return self.service.schedule_action('reset').wait(die=True)

    def enable_vnc(self):
        return self.service.schedule_action('enable_vnc').wait(die=True)

    def disable_vnc(self):
        return self.service.schedule_action('disable_vnc').wait(die=True)

    def add_portforward(self, name, source, target):
        return self.service.schedule_action('add_portforward', args={'name': name, 'source': source, 'target': target}).wait(die=True)

    def remove_portforward(self, name):
        return self.service.schedule_action('remove_portforward', args={'name': name}).wait(die=True).wait(die=True)