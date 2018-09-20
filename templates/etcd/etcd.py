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
        self.data['clientPort'] = etcd_sal.client_port
        self.data['peerPort'] = etcd_sal.peer_port

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
            'name': self.name,
            'node': self._node_sal,
            'listen_peer_urls': self.data['listenPeerUrls'],
            'listen_client_urls': self.data['listenClientUrls'],
            'initial_advertise_peer_urls': self.data['initialAdvertisePeerUrls'],
            'advertise_client_urls': self.data['advertiseClientUrls'],
            'client_port': self.data['clientPort'],
            'peer_port': self.data['peerPort'],
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
        return {
            'ip': self._node_sal.public_addr,
            'client_port': self.data['clientPort'],
            'peer_port': self.data['peerPort']
        }
    
    def update_urls(self, data):
        self.data['listenPeerUrls'] = data.get('listenPeerUrls', self.data['listenPeerUrls'])
        self.data['listenClientUrls'] = data.get('listenClientUrls', self.data['listenClientUrls'])
        self.data['initialAdvertisePeerUrls'] = data.get('initialAdvertisePeerUrls', self.data['initialAdvertisePeerUrls'])
        self.data['advertiseClientUrls'] = data.get('advertiseClientUrls', self.data['advertiseClientUrls'])
    
    def insert_record(self, key, value):
        self.state.check('status', 'running', 'ok')
        self._etcd_sal.put(key, value)