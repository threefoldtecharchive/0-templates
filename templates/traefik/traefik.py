from jumpscale import j
from zerorobot.template.base import TemplateBase


ETCD_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/etcd/0.0.1'

NODE_CLIENT = 'local'

class Traefik(TemplateBase):
    version = '0.0.1'
    template_name = 'traefik'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self._url_ = None
        self._node_ = None
        self.etcd = self._etcd

    @property
    def _node_sal(self):
        """
        connection to the node
        """
        return j.clients.zos.get(NODE_CLIENT)

    @property
    def _node(self):
        if not self._node_:
            self._node_ = self.api.services.get(template_account='threefoldtech', template_name='node')
        return self._node_

    @property
    def _traefik_sal(self):
        kwargs = {
            'name': self.name,
            'node': self._node_sal,
            'etcd_watch':self.data['etcdWatch'],
            'etcd_endpoint': self.etc_url
        }
        return j.sal_zos.traefik.get(**kwargs)
    @property
    def _etcd(self):
        return self.api.services.get(template_uid=ETCD_TEMPLATE_UID, name=self.data['etcdServerName'])

    def etc_url(self):
        self.state.check('actions', 'install', 'ok')
        result = self._etcd.schedule_action('connection_info').wait(die=True).result
        return '{}:{}'.format(result['ip'], result['client_port'])
        

    def node_port(self):
        return self.data['nodePort']

    def install(self):
        self.logger.info('Installing traefik %s' % self.name)

        traefik_sal = self._traefik_sal

        self.data['nodePort'] = traefik_sal.node_port
        self.logger.info('Install traefik %s is Done' % self.name)
        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        self.logger.info('Uninstalling traefik %s' % self.name)
        self._traefik_sal.destroy()
        self.state.delete('actions', 'install')
        self.state.delete('status', 'running')

    def start(self):
        """
        start traefik server
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Starting traefik  %s' % self.name)
        self._traefik_sal.start()
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def stop(self):
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Stopping traefik %s' % self.name)
        self._traefik_sal.stop()
        self.state.delete('actions', 'start')
        self.state.delete('status', 'running')

    def Add_key_value(self,url_frontend, url_backend):
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Adding to conf %s' % self.name)
        self._traefik_sal.key_value_storage(url_frontend, url_backend)