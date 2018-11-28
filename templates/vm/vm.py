import copy

from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry
from zerorobot.template.state import StateCheckError

from JumpscaleLib.sal_zos.globals import TIMEOUT_DEPLOY
NODE_CLIENT = 'local'
VDISK_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/vdisk/0.0.1'
PORT_MANAGER_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/node_port_manager/0.0.1'


class Vm(TemplateBase):

    version = '0.0.1'
    template_name = "vm"

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)

        self.add_delete_callback(self.uninstall)
        self.recurring_action('_monitor', 30)  # every 30 seconds
        self.recurring_action('_load_info', 60*60)  # every hour

    def validate(self):
        if not (self.data['flist'] or self.data['ipxeUrl']):
            raise ValueError("invalid input. Vm requires flist or ipxeUrl to be specifed.")

        for disk in self.data['disks']:
            if 'url' not in disk:
                disk['url'] = ''

    @property
    def _vm_sal(self):
        node_sal = self._node_sal
        self.data['ports'] = self._populate_port_forwards(self.data['ports'])

        data = self.data.copy()
        data['name'] = self.name

        return node_sal.primitives.from_dict('vm', data)

    @property
    def _node_sal(self):
        """
        connection to the zos node
        """
        return j.clients.zos.get(NODE_CLIENT)

    def _monitor(self):
        self.logger.info('Monitor vm %s' % self.name)
        try:
            self.state.check('actions', 'install', 'ok')
            self.state.check('actions', 'start', 'ok')
        except StateCheckError:
            return

        vm_sal = self._vm_sal

        if not vm_sal.is_running():
            for disk in self.data['disks']:
                vdisk = self.api.services.get(template_uid=VDISK_TEMPLATE_UID, name=disk['name'])
                try:
                    vdisk.state.check('status', 'running', 'ok')  # Cannot start vm until vdisks are running
                except StateCheckError:
                    self.state.delete('status', 'running')
                    raise

            self._update_vdisk_url()
            vm_sal.deploy()

            if not vm_sal.is_running():
                self.state.delete('status', 'running')
            else:
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

    def update_kernelargs(self, kernel_args):
        self.data['kernelArgs'] = kernel_args

    def generate_identity(self):
        self.data['ztIdentity'] = self._node_sal.generate_zerotier_identity()
        return self.data['ztIdentity']

    def _update_vdisk_url(self):
        self.logger.info('update the vdisk url')
        for disk in self.data['disks']:
            vdisk = self.api.services.get(template_uid=VDISK_TEMPLATE_UID, name=disk['name'])
            disk['url'] = vdisk.schedule_action('private_url').wait(die=True).result
            self.data['info'] = None # force relaod if info action data

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

        self._release_ports()

        self.data['info'] = None # force relaod if info action data
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

    def info(self, timeout=TIMEOUT_DEPLOY):
        self.logger.info('get vm info')
        if not self.data.get('info') or not self.data['info'].get('nics'):
            self._load_info(timeout)
        return self.data['info']

    def _load_info(self, timeout):
        self.logger.info('load the vm info')
        self._update_vdisk_url()
        info = self._vm_sal.info or {}
        nics = copy.deepcopy(self.data['nics'])
        self.logger.info('vm nics : {}'.format(nics))
        for nic in nics:
            if nic['type'] == 'zerotier' and nic.get('ztClient') and self.data.get('ztIdentity'):
                self.logger.info('get the vm zerotier data')
                ztAddress = self.data['ztIdentity'].split(':')[0]
                self.logger.inf('ztAddress : {}'.format(ztAddress))
                zclient = j.clients.zerotier.get(nic['ztClient'])
                try:
                    network = zclient.network_get(nic['id'])
                    self.logger.info('network : {}'.format(network))
                    member = network.member_get(address=ztAddress)
                    self.logger.info('member : {}'.format(member))
                    member.timeout = timeout
                    self.logger.info('get private ip timeout : {}'.format(timeout))
                    nic['ip'] = member.get_private_ip(timeout)
                except (RuntimeError, ValueError) as e:
                    self.logger.warning('Failed to retreive zt ip: %s', str(e))
        self.logger.info('construct the vm data dict')
        node_sal = self._node_sal
        self.data['info'] = {
            'vnc': info.get('vnc'),
            'status': info.get('state', 'halted'),
            'disks': self.data['disks'],
            'nics': nics,
            'ztIdentity': self.data['ztIdentity'],
            'ports': {p['source']: p['target'] for p in self.data['ports']},
            'host': {
                'storage_addr': node_sal.storage_addr,
                'public_addr': node_sal.public_addr,
                'management_addr': node_sal.management_address,
            }
        }
        return self.data['info']

    def disable_vnc(self):
        self.logger.info('Disable vnc for vm %s' % self.name)
        self.state.check('actions', 'install', 'ok')
        self._vm_sal.disable_vnc()

    def add_portforward(self, name, target, source=None):
        for forward in list(self.data['ports']):
            if forward['name'] == name and (forward['target'] != target or source and source != forward['source']):
                raise RuntimeError("port forward with name {} already exist for a different target or a different source".format(name))
            elif forward['name'] == name:
                return forward

        node_sal = self._node_sal
        forward = {
            'name': name,
            'target': target,
            'source': source,
        }
        forward = self._populate_port_forwards([forward])[0]
        self.data['ports'].append(forward)

        node_sal.client.kvm.add_portfoward(self._vm_sal.uuid, forward['source'], forward['target'])

        self.data['info'] = None # force relaod if info action data
        return forward

    def remove_portforward(self, name):
        for forward in list(self.data['ports']):
            if forward['name'] == name:
                self._node_sal.client.kvm.remove_portfoward(self._vm_sal.uuid, str(forward['source']), forward['target'])
                self.data['ports'].remove(forward)
                self.data['info'] = None # force relaod if info action data
                return

    def _populate_port_forwards(self, ports):
        ports = copy.deepcopy(ports)
        # count how many port we need to find
        count = 0
        for pf in ports:
            if not pf.get('source'):
                count += 1

        if count > 0:
            # ask the port manager 'count' number of free port
            free_ports = self._reserve_ports(count)
            # assigned the free port to the forward where source is missing
            for i, pf in enumerate(ports):
                if not pf.get('source'):
                    ports[i]['source'] = free_ports.pop()

        return ports

    @retry(exceptions=ServiceNotFoundError, tries=3, delay=3, backoff=2)
    def _reserve_ports(self, count):
        port_mgr = self.api.services.get(template_uid=PORT_MANAGER_TEMPLATE_UID, name='_port_manager')
        free_ports = port_mgr.schedule_action("reserve", {"service_guid": self.guid, 'n': count}).wait(die=True).result
        return free_ports

    @retry(exceptions=ServiceNotFoundError, tries=3, delay=3, backoff=2)
    def _release_ports(self):
        port_mgr = self.api.services.get(template_uid=PORT_MANAGER_TEMPLATE_UID, name='_port_manager')
        ports = [x['source'] for x in self.data['ports']]
        if not ports:
            return
        port_mgr.schedule_action("release", {"service_guid": self.guid, 'ports': ports})
        for port in self.data['ports']:
            port['source'] = None
