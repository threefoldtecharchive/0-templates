from jumpscale import j

from zerorobot.template.base import TemplateBase


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
        self._etcd_sal.start()
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
        self.state.delete('status', 'running')

    def connection_info(self):
        self.state.check('status', 'running', 'ok')
        etcd_sal = self._etcd_sal
        return {'peer_url': etcd_sal.peer_url, 'client_url': etcd_sal.client_url}
    
    def update_cluster(self, cluster):
        self.data['cluster'] = cluster
    
    def insert_record(self, key, value):
        self.state.check('status', 'running', 'ok')
        self._etcd_sal.put(key, value)

    def get_record(self, key):
        self.state.check('status', 'running', 'ok')
        return self._etcd_sal.get(key)
