from jumpscale import j
from zerorobot.template.base import TemplateBase

NODE_CLIENT = 'local'


class Coredns(TemplateBase):
    version = '0.0.1'
    template_name = 'coredns'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.add_delete_callback(self.uninstall)
        self.recurring_action('_monitor', 30)  # every 30 seconds

    def validate(self):
        self.state.delete('status', 'running')
        for nic in self.data['nics']:
            if nic['type'] == 'zerotier':
                break
        else:
            raise ValueError('Service must contain at least one zerotier nic')

        for key in ['etcdEndpoint', 'etcdPassword']:
            if not self.data[key]:
                raise ValueError('Invalid value for {}'.format(key))

        # If backplane is empty get the interface name from the public ip
        if not self.data['backplane']:
            self.data['backplane'] = self._node_sal.get_nic_by_ip(self._node_sal.network.get_management_info())['name']

    def _monitor(self):
        self.logger.info('Monitor coredns %s' % self.name)
        self.state.check('actions', 'start', 'ok')

        if not self._coredns_sal.is_running():
            self.state.set('status', 'running', 'error')
            self._coredns_sal.deploy()
            self._coredns_sal.start()
            if self._coredns_sal.is_running():
                self.state.set('status', 'running', 'ok')
        else:
            self.state.set('status', 'running', 'ok')

    @property
    def _node_sal(self):
        """
        connection to the node
        """
        return j.clients.zos.get(NODE_CLIENT)

    @property
    def _coredns_sal(self):
        kwargs = {
            'name': self.name,
            'node': self._node_sal,
            'zt_identity': self.data['ztIdentity'],
            'nics': self.data['nics'],
            'backplane': self.data['backplane'],
            'etcd_endpoint': self.data['etcdEndpoint'],
            'etcd_password': self.data['etcdPassword'],
            'domain': self.data['domain'],
        }
        return j.sal_zos.coredns.get(**kwargs)

    def install(self):
        self.logger.info('Installing CoreDns %s' % self.name)

        coredns_sal = self._coredns_sal

        coredns_sal.deploy()
        self.data['ztIdentity'] = coredns_sal.zt_identity
        self.logger.info('Install CoreDns %s is Done' % self.name)
        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        self.logger.info('Uninstalling CoreDns %s' % self.name)
        self._coredns_sal.destroy()
        self.state.delete('actions', 'install')
        self.state.delete('actions', 'start')
        self.state.delete('status', 'running')

    def start(self):
        """
        start coredns server
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Starting CoreDns  %s' % self.name)
        self._coredns_sal.deploy()
        self._coredns_sal.start()
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def stop(self):
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Stopping CoreDns %s' % self.name)
        self._coredns_sal.stop()
        self.state.delete('actions', 'start')
        self.state.delete('status', 'running')

    def update_endpoint(self, etcd_endpoint):
        self.data['etcdEndpoint'] = etcd_endpoint
        self.state.check('actions', 'start', 'ok')
        self._coredns_sal.stop()
        self._coredns_sal.start()
