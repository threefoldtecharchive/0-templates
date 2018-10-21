from jumpscale import j
from zerorobot.template.base import TemplateBase

NODE_CLIENT = 'local'


class Traefik(TemplateBase):
    version = '0.0.1'
    template_name = 'traefik'

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

    def _monitor(self):
        self.logger.info('Monitor traefik %s' % self.name)
        self.state.check('actions', 'start', 'ok')

        if not self._traefik_sal.is_running():
            self.state.delete('status', 'running')
            self._traefik_sal.deploy()
            self._traefik_sal.start()
            if self._traefik_sal.is_running():
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
    def _traefik_sal(self):
        kwargs = {
            'name': self.name,
            'node': self._node_sal,
            'etcd_watch':self.data['etcdWatch'],
            'zt_identity': self.data['ztIdentity'],
            'nics': self.data['nics'],
            'etcd_endpoint': self.data['etcdEndpoint'],
            'etcd_password': self.data['etcdPassword'],
        }
        return j.sal_zos.traefik.get(**kwargs)

    def install(self):
        self.logger.info('Installing traefik %s' % self.name)

        traefik_sal = self._traefik_sal
        traefik_sal.deploy()
        self.data['ztIdentity'] = traefik_sal.zt_identity
        self.logger.info('Install traefik %s is Done' % self.name)
        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        self.logger.info('Uninstalling traefik %s' % self.name)
        self._traefik_sal.destroy()
        self.state.delete('actions', 'install')
        self.state.delete('actions', 'start')
        self.state.delete('status', 'running')

    def start(self):
        """
        start traefik server
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Starting traefik  %s' % self.name)
        self._traefik_sal.deploy()
        self._traefik_sal.start()
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def stop(self):
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Stopping traefik %s' % self.name)
        self._traefik_sal.stop()
        self.state.delete('actions', 'start')
        self.state.delete('status', 'running')
