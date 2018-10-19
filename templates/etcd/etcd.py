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

        self.data['password'] = self.data['password'] if self.data['password'] else j.data.idgenerator.generateXCharID(10)

    def _deploy(self):
        etcd_sal = self._etcd_sal
        etcd_sal.deploy()
        self.data['ztIdentity'] = etcd_sal.zt_identity
        

    def _monitor(self):
        self.logger.info('Monitor etcd %s' % self.name)
        self.state.check('actions', 'start', 'ok')

        if not self._etcd_sal.is_running():
            self.state.delete('status', 'running')
            self._deploy()
            self._etcd_sal.start()
            if self._etcd_sal.is_running():
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
        self.state.check('actions', 'install', 'ok')
        return self._etcd_sal.connection_info()
    
    def update_cluster(self, cluster):
        self.data['cluster'] = cluster
        try:
            self.state.check('actions', 'start', 'ok')
            self._etcd_sal.stop()
            self._etcd_sal.start()
        except StateCheckError:
            pass