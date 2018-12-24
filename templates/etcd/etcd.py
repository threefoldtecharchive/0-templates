from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError

NODE_CLIENT = 'local'


class Etcd(TemplateBase):

    version = '0.0.1'
    template_name = "etcd"

    def __init__(self, name=None, guid=None, data=None):
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

        self.data['password'] = self.data['password'] if self.data['password'] else j.data.idgenerator.generateXCharID(
            16)
        self.data['token'] = self.data['token'] if self.data['token'] else self.guid

    def _deploy(self):
        etcd_sal = self._etcd_sal
        etcd_sal.deploy()
        self.data['ztIdentity'] = etcd_sal.zt_identity

    def _monitor(self):
        try:
            self.state.check('actions', 'start', 'ok')
        except StateCheckError:
            return

        self.logger.info('Monitor etcd %s' % self.name)

        etcd_sal = self._etcd_sal
        if not etcd_sal.is_running():
            self.state.delete('status', 'running')
            self._deploy()
            etcd_sal.start()
            if etcd_sal.is_running():
                self.state.set('status', 'running', 'ok')
        else:
            self.state.set('status', 'running', 'ok')

    @property
    def _node_sal(self):
        return j.clients.zos.get(NODE_CLIENT)

    @property
    def _etcd_sal(self):
        kwargs = {
            'name': self.guid,
            'node': self._node_sal,
            'zt_identity': self.data['ztIdentity'],
            'nics': self.data['nics'],
            'token': self.data['token'],
            'cluster': self.data['cluster'],
            'password': self.data['password'],
        }
        return j.sal_zos.etcd.get(**kwargs)

    def install(self):
        self.logger.info('Installing etcd %s' % self.name)
        self._deploy()
        self.state.set('actions', 'install', 'ok')

    def start(self):
        """
        start etcd server
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Starting etcd %s' % self.name)
        self._deploy()
        etcd_sal = self._etcd_sal
        etcd_sal.start()
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def stop(self):
        """
        stop etcd server
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Stopping etcd %s' % self.name)
        self._etcd_sal.stop()
        self.state.delete('actions', 'start')
        self.state.delete('status', 'running')

    def uninstall(self):
        self.logger.info('Uninstalling etcd %s' % self.name)
        self._etcd_sal.destroy()
        self.state.delete('actions', 'install')
        self.state.delete('actions', 'start')
        self.state.delete('status', 'running')

    def connection_info(self):
        # connection info depends on the container running but not on the process
        # @todo: if someone stops the service, that would kill the container and this will crash.
        # may be we should add a state just for the connection
        self.state.check('actions', 'install', 'ok')
        return self._etcd_sal.connection_info()

    def update_cluster(self, cluster):
        self.data['cluster'] = cluster
        etcd_sal = self._etcd_sal
        if etcd_sal.is_running():
            etcd_sal.stop()
            etcd_sal.start()

    def _enable_auth(self):
        self._etcd_sal.enable_auth()

    def _prepare_traefik(self):
        self._etcd_sal.prepare_traefik()
