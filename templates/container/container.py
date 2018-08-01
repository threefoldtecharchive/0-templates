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

    def validate(self):
        for param in ['flist']:
            if not self.data[param]:
                raise ValueError("parameter '%s' not valid: %s" % (param, str(self.data[param])))

    @property
    def node_sal(self):
        return j.sal_zos.node.get(NODE_CLIENT)

    @property
    def container_sal(self):
        try:
            return self.node_sal.containers.get(self.name)
        except LookupError:
            self.install()
            return self.node_sal.containers.get(self.name)

    def install(self):
        # convert "src:dst" to {src:dst}
        ports = j.sal_zos.format_ports(self.data['ports'])

        mounts = {}
        for mount in self.data['mounts']:
            mounts[mount['source']] = mount['target']

        envs = {}
        for env in self.data['env']:
            envs[env['name']] = env['value']

        self.node_sal.containers.create(self.name, self.data['flist'], hostname=self.data['hostname'],
                                        mounts=mounts, nics=self.data['nics'],
                                        host_network=self.data['hostNetworking'],
                                        ports=ports, storage=self.data['storage'],
                                        init_processes=self.data['initProcesses'],
                                        privileged=self.data['privileged'], env=envs)
        self.state.set('actions', 'install', 'ok')
        self.state.set('actions', 'start', 'ok')

    def add_nic(self, nic):
        for existing_nic in self.data['nics']:
            if self._compare_objects(existing_nic, nic, 'type', 'id'):
                raise ValueError('Nic with same type/id combination already exists')
        self.data['nics'].append(nic)
        self.container_sal.add_nic(nic)

    def remove_nic(self, nicname):
        self.container_sal.remove_nic(nicname)

    def _compare_objects(self, obj1, obj2, *keys):
        for key in keys:
            if obj1[key] != obj2[key]:
                return False
        return True

    def start(self):
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Starting container %s' % self.name)
        self.container_sal.start()
        self.state.set('actions', 'start', 'ok')

    def stop(self):
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Stopping container %s' % self.name)
        self.container_sal.stop()
        self.state.delete('actions', 'start')

    def uninstall(self):
        self.logger.info('Uninstalling container %s' % self.name)
        self.stop()
        self.state.delete('actions', 'install')
