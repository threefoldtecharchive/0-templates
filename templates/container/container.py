import copy

from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError

from jumpscale import j

NODE_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/node/0.0.1'
NODE_CLIENT = 'local'


class Container(TemplateBase):

    version = '0.0.1'
    template_name = "container"

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.recurring_action('_monitor', 30)  # every 30 seconds
        self._container = None
        self._node_sal = j.clients.zos.get(NODE_CLIENT)

    def validate(self):
        for param in ['flist']:
            if not self.data[param]:
                raise ValueError("parameter '%s' not valid: %s" % (param, str(self.data[param])))

    @property
    def _container_sal(self):
        if not self._container:
            self.install()
            self._container = self._node_sal.containers.get(self.name)
        return self._container

    def _monitor(self):
        try:
            self.state.check('actions', 'start', 'ok')
        except StateCheckError:
            return

        self.logger.info('Monitor container %s' % self.name)
        if not self._container_sal.is_running():
            self.state.set('status', 'running', 'error')
            self.install()
            if self._container_sal.is_running():
                self.state.set('status', 'running', 'ok')
        else:
            self.state.set('status', 'running', 'ok')

    def install(self):
        # convert "src:dst" to {src:dst}
        ports = {}
        for p in self.data['ports']:
            src, dst = p.split(":")
            ports[src] = int(dst)

        mounts = {}
        for mount in self.data['mounts']:
            mounts[mount['source']] = mount['target']

        envs = {}
        for env in self.data['env']:
            envs[env['name']] = env['value']

        self._container = self._node_sal.containers.create(self.name, self.data['flist'], hostname=self.data['hostname'],
                                                           mounts=mounts, nics=copy.deepcopy(self.data['nics']),
                                                           host_network=self.data['hostNetworking'],
                                                           ports=ports, storage=self.data['storage'],
                                                           init_processes=self.data['initProcesses'],
                                                           privileged=self.data['privileged'], identity=self.data['ztIdentity'],
                                                           env=envs)
        self.data['ztIdentity'] = self._container_sal.identity

        self.state.set('actions', 'install', 'ok')
        self.state.set('actions', 'start', 'ok')

    def add_nic(self, nic):
        for existing_nic in self.data['nics']:
            if self._compare_objects(existing_nic, nic, 'type', 'id'):
                raise ValueError('Nic with same type/id combination already exists')
        self.data['nics'].append(nic)
        self._container_sal.add_nic(nic)

    def remove_nic(self, nicname):
        for nic in self.data['nics']:
            if nicname == nic['name']:
                break
        else:
            raise ValueError('Nic {} does not exist'.format(nicname))
        self._container_sal.remove_nic(nicname)

    def _compare_objects(self, obj1, obj2, *keys):
        for key in keys:
            if obj1[key] != obj2[key]:
                return False
        return True

    def start(self):
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Starting container %s' % self.name)
        self._container_sal.start()
        self.state.set('actions', 'start', 'ok')

    def stop(self):
        self.state.check('actions', 'start', 'ok')
        self._stop()

    def _stop(self):
        self.logger.info('Stopping container %s' % self.name)
        try:
            self._node_sal.containers.get(self.name)
            self._container_sal.stop()
            self._container = None
        except LookupError:
            pass
        self.state.delete('actions', 'start')

    def uninstall(self):
        self._stop()
        self.state.delete('actions', 'install')
