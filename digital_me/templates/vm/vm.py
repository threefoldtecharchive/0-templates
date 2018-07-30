from js9 import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError
from zerorobot.template.decorator import timeout
from requests import HTTPError

VDISK_TEMPLATE_UID = 'github.com/zero-os/0-templates/vdisk/0.0.1'
VM_TEMPLATE_UID = 'github.com/zero-os/0-templates/vm/0.0.1'
ZT_TEMPLATE_UID = 'github.com/zero-os/0-templates/zerotier_client/0.0.1'
BASEFLIST = 'https://hub.gig.tech/gig-bootable/{}.flist'
ZEROOSFLIST = "https://hub.gig.tech/gig-bootable/zero-os-bootable.flist"
IPXEURL = 'https://bootstrap.gig.tech/ipxe/{}/{}/development ztid={}'


class Vm(TemplateBase):

    version = '0.0.1'
    template_name = "vm"

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.add_delete_callback(self.uninstall)

        self.recurring_action('_monitor', 30)  # every 30 seconds
        self._node_api = None
        self._node_robot_url = None

    def validate(self):
        if not self.data['nodeId']:
            raise ValueError('Invalid input, Vm requires nodeId')

        capacity = j.clients.grid_capacity.get(interactive=False)
        try:
            node, _ = capacity.api.GetCapacity(self.data['nodeId'])
        except HTTPError as err:
            if err.response.status_code == 404:
                raise ValueError('Node {} does not exist'.format(self.data['nodeId']))
            raise err

        j.clients.zrobot.get(self.data['nodeId'], data={'url': node.robot_address})
        self._node_api = j.clients.zrobot.robots[self.data['nodeId']]
        self._node_robot_url = node.robot_address

        if self.data['image'].partition(':')[0] not in ['zero-os', 'ubuntu']:
            raise ValueError('Invalid image')

        for key in ['id', 'ztClient']:
            if not self.data['zerotier'].get(key):
                raise ValueError('Invalid input, zerotier requires {}'.format(key))

    @property
    def _node_vm(self):
        return self._node_api.services.get(name=self.guid)

    def _monitor(self):
        self.logger.info('Monitor vm %s' % self.name)
        self.state.check('actions', 'install', 'ok')

        @timeout(10)
        def update_state():
            state = self._node_vm.state
            try:
                state.check('status', 'running', 'ok')
                self.state.set('status', 'running', 'ok')
                return
            except StateCheckError:
                self.state.delete('status', 'running')

        try:
            update_state()
        except:
            self.state.delete('status', 'running')

    def install(self):
        self.logger.info('Installing vm %s' % self.name)

        zt_name = self.data['zerotier']['ztClient']
        zt_client = self.api.services.get(name=zt_name, template_uid=ZT_TEMPLATE_UID)
        data = {'url': self._node_robot_url, 'serviceguid': self.guid}
        zt_client.schedule_action('add_to_robot', args=data).wait(die=True)

        vm_disks = []
        for disk in self.data['disks']:
            vdisk = self._node_api.services.find_or_create(VDISK_TEMPLATE_UID, '_'.join([self.guid, disk['label']]), data=disk)
            vdisk.schedule_action('install').wait(die=True)
            vm_disks.append({
                'name': vdisk.name,
                'mountPoint': disk['mountPoint'],
                'filesystem': disk['filesystem'],
                'label': disk['label'],
            })

        vm_data = {
            'memory': self.data['memory'],
            'cpu': self.data['cpu'],
            'disks': vm_disks,
            'configs': self.data['configs'],
            'ztIdentity': self.data['ztIdentity'],
            'nics': [{
                'id': self.data['zerotier']['id'],
                'type': 'zerotier',
                'ztClient': self.guid,
                'name': 'zerotier_nic',
            },
                {'name': 'test',
                 'type': 'default'
                 }]
        }

        image, _, version = self.data['image'].partition(':')
        if image == 'zero-os':
            version = version or 'development'
            vm_data['flist'] = ZEROOSFLIST
        else:
            version = version or 'lts'
            flist = '{}:{}'.format(image, version)
            vm_data['flist'] = BASEFLIST.format(flist)

        vm = self._node_api.services.find_or_create(VM_TEMPLATE_UID, self.guid, data=vm_data)

        if image == 'zero-os':
            if not self.data['ztIdentity']:
                self.data['ztIdentity'] = vm.schedule_action('generate_identity').wait(die=True).result
            url = IPXEURL.format(version, self.data['zerotier']['id'], self.data['ztIdentity'])
            vm.schedule_action('update_ipxeurl', args={'url': url}).wait(die=True)

        vm.schedule_action('install').wait(die=True)
        self.data['ztIdentity'] = vm.schedule_action('zt_identity').wait(die=True).result

        self.state.set('actions', 'install', 'ok')
        self.state.set('status', 'running', 'ok')

    def zt_identity(self):
        return self.data['ztIdentity']

    def uninstall(self):
        self.logger.info('Uninstalling vm %s' % self.name)
        try:
            self._node_vm.schedule_action('uninstall').wait(die=True)
            self._node_vm.delete()
        except ServiceNotFoundError:
            pass

        for disk in self.data['disks']:
            try:
                vdisk = self._node_api.services.get(
                    template_uid=VDISK_TEMPLATE_UID, name='_'.join([self.guid, disk['label']]))
                vdisk.schedule_action('uninstall').wait(die=True)
                vdisk.delete()
            except ServiceNotFoundError:
                pass

        try:
            zt_name = self.data['zerotier']['ztClient']
            zt_client = self.api.services.get(name=zt_name, template_uid=ZT_TEMPLATE_UID)
            data = {'url': self._node_robot_url, 'serviceguid': self.guid}
            zt_client.schedule_action('remove_from_robot', args=data).wait(die=True)
        except ServiceNotFoundError:
            pass

        self.state.delete('actions', 'install')
        self.state.delete('status', 'running')

    def info(self, timeout=None):
        self.state.check('actions', 'install', 'ok')
        info = self._node_vm.schedule_action('info', args={'timeout': timeout}).wait(die=True).result
        nics = info.pop('nics')
        nic = nics[0]
        info['zerotier'] = {'id': nic['id'],
                            'ztClient': self.data.get('zerotier', {}).get('ztClient'),
                            'ip': nic.get('ip')}
        return info

    def shutdown(self):
        self.logger.info('Shuting down vm %s' % self.name)
        self.state.check('status', 'running', 'ok')
        self._node_vm.schedule_action('shutdown').wait(die=True)
        self.state.delete('status', 'running')
        self.state.set('status', 'shutdown', 'ok')

    def pause(self):
        self.logger.info('Pausing vm %s' % self.name)
        self.state.check('status', 'running', 'ok')
        self._node_vm.schedule_action('pause').wait(die=True)
        self.state.delete('status', 'running')
        self.state.set('actions', 'pause', 'ok')

    def resume(self):
        self.logger.info('Resuming vm %s' % self.name)
        self.state.check('actions', 'pause', 'ok')
        self._node_vm.schedule_action('resume').wait(die=True)
        self.state.delete('actions', 'pause')
        self.state.set('status', 'running', 'ok')

    def reboot(self):
        self.logger.info('Rebooting vm %s' % self.name)
        self.state.check('actions', 'install', 'ok')
        self._node_vm.schedule_action('reboot').wait(die=True)
        self.state.set('status', 'rebooting', 'ok')

    def reset(self):
        self.logger.info('Resetting vm %s' % self.name)
        self.state.check('actions', 'install', 'ok')
        self._node_vm.schedule_action('reset').wait(die=True)

    def enable_vnc(self):
        self.logger.info('Enable vnc for vm %s' % self.name)
        self.state.check('actions', 'install', 'ok')
        self._node_vm.schedule_action('enable_vnc').wait(die=True)

    def disable_vnc(self):
        self.logger.info('Disable vnc for vm %s' % self.name)
        self.state.check('actions', 'install', 'ok')
        self._node_vm.schedule_action('disable_vnc').wait(die=True)
