from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError
import copy

NODE_CLIENT = 'local'
VDISK_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/vdisk/0.0.1'


class Vm(TemplateBase):

    version = '0.0.1'
    template_name = "vm"

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)

        self.add_delete_callback(self.uninstall)
        self.recurring_action('_monitor', 30)  # every 30 seconds

    def validate(self):
        if not (self.data['flist'] or self.data['ipxeUrl']):
            raise ValueError("invalid input. Vm requires flist or ipxeUrl to be specifed.")

        for disk in self.data['disks']:
            if 'url' not in disk:
                disk['url'] = ''

    @property
    def _vm_sal(self):
        self.data['ports'] = populate_port_forwards(self.data['ports'], self._node_sal)

        data = self.data.copy()
        data['name'] = self.name

        return self._node_sal.primitives.from_dict('vm', data)

    @property
    def _node_sal(self):
        """
        connection to the zos node
        """
        return j.clients.zos.get(NODE_CLIENT)

    def _monitor(self):
        self.logger.info('Monitor vm %s' % self.name)
        self.state.check('actions', 'install', 'ok')
        self.state.check('actions', 'start', 'ok')

        vm_sal = self._vm_sal

        if not vm_sal.is_running():
            self.state.delete('status', 'running')

            for disk in self.data['disks']:
                vdisk = self.api.services.get(template_uid=VDISK_TEMPLATE_UID, name=disk['name'])
                vdisk.state.check('status', 'running', 'ok')  # Cannot start vm until vdisks are running

            self._update_vdisk_url()
            vm_sal.deploy()

            if vm_sal.is_running():
                self.state.set('status', 'running', 'ok')
        else:
            self.state.set('status', 'running', 'ok')

        # handle reboot
        try:
            self.state.check('status', 'running', 'ok')
            self.state.check('status', 'rebooting', 'ok')
            self.state.delete('status', 'rebooting')
        except StateCheckError:
            pass

    def update_ipxeurl(self, url):
        self.data['ipxeUrl'] = url

    def generate_identity(self):
        self.data['ztIdentity'] = self._node_sal.generate_zerotier_identity()
        return self.data['ztIdentity']

    def _update_vdisk_url(self):
        for disk in self.data['disks']:
            vdisk = self.api.services.get(template_uid=VDISK_TEMPLATE_UID, name=disk['name'])
            disk['url'] = vdisk.schedule_action('private_url').wait(die=True).result

    def install(self):
        self.logger.info('Installing vm %s' % self.name)
        self._update_vdisk_url()
        vm_sal = self._vm_sal
        vm_sal.deploy()
        self.data['uuid'] = vm_sal.uuid
        self.data['ztIdentity'] = vm_sal.zt_identity

        self.state.set('actions', 'install', 'ok')
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def zt_identity(self):
        return self.data['ztIdentity']

    def uninstall(self):
        self.logger.info('Uninstalling vm %s' % self.name)
        self._vm_sal.destroy()
        self.state.delete('actions', 'install')
        self.state.delete('actions', 'start')
        self.state.delete('status', 'running')

    def shutdown(self, force=False):
        self.logger.info('Shuting down vm %s' % self.name)
        self.state.check('status', 'running', 'ok')
        if force is False:
            self._vm_sal.shutdown()
        else:
            self._vm_sal.destroy()
        self.state.delete('status', 'running')
        self.state.delete('actions', 'start')

    def pause(self):
        self.logger.info('Pausing vm %s' % self.name)
        self.state.check('status', 'running', 'ok')
        self._vm_sal.pause()
        self.state.delete('status', 'running')
        self.state.set('actions', 'pause', 'ok')

    def start(self):
        self.logger.info('Starting vm {}'.format(self.name))
        self.state.set('actions', 'install', 'ok')
        self._update_vdisk_url()
        self._vm_sal.deploy()
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def resume(self):
        self.logger.info('Resuming vm %s' % self.name)
        self.state.check('actions', 'pause', 'ok')
        self._update_vdisk_url()
        self._vm_sal.resume()
        self.state.delete('actions', 'pause')
        self.state.set('status', 'running', 'ok')
        self.state.set('actions', 'start', 'ok')

    def reboot(self):
        self.logger.info('Rebooting vm %s' % self.name)
        self.state.check('actions', 'install', 'ok')
        self._update_vdisk_url()
        self._vm_sal.reboot()
        self.state.set('status', 'rebooting', 'ok')

    def reset(self):
        self.logger.info('Resetting vm %s' % self.name)
        self.state.check('actions', 'install', 'ok')
        self._vm_sal.reset()

    def enable_vnc(self):
        self.logger.info('Enable vnc for vm %s' % self.name)
        self.state.check('actions', 'install', 'ok')
        self._vm_sal.enable_vnc()

    def info(self, timeout=None):
        self._update_vdisk_url()
        info = self._vm_sal.info or {}
        nics = copy.deepcopy(self.data['nics'])
        for nic in nics:
            if nic['type'] == 'zerotier' and nic.get('ztClient') and self.data.get('ztIdentity'):
                ztAddress = self.data['ztIdentity'].split(':')[0]
                zclient = j.clients.zerotier.get(nic['ztClient'])
                try:
                    network = zclient.network_get(nic['id'])
                    member = network.member_get(address=ztAddress)
                    member.timeout = None
                    nic['ip'] = member.get_private_ip(timeout)
                except (RuntimeError, ValueError) as e:
                    self.logger.warning('Failed to retreive zt ip: %s', str(e))

        return {
            'vnc': info.get('vnc'),
            'status': info.get('state', 'halted'),
            'disks': self.data['disks'],
            'nics': nics,
            'ztIdentity': self.data['ztIdentity'],
            'ports': {p['source']: p['target'] for p in self.data['ports']}
        }

    def disable_vnc(self):
        self.logger.info('Disable vnc for vm %s' % self.name)
        self.state.check('actions', 'install', 'ok')
        self._vm_sal.disable_vnc()


def populate_port_forwards(ports, node_sal):
    # count how many port we need to find
    count = 0
    for pf in ports:
        if not pf.get('source'):
            count += 1

    if count > 0:
        # ask zero-os 'count' number of free port
        free_ports = node_sal.free_ports(count)
        # assigned the free port to the forward where source is missing
        for i, pf in enumerate(ports):
            if not pf.get('source'):
                ports[i]['source'] = free_ports.pop()

    return ports
