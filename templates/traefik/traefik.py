from jumpscale import j
from zerorobot.template.base import TemplateBase


ETCD_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/etcd/0.0.1'

NODE_CLIENT = 'local'

class Traefik(TemplateBase):
    version = '0.0.1'
    template_name = 'traefik'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self._node_ = None
        self.add_delete_callback(self.uninstall)
        self.recurring_action('_monitor', 30)  # every 30 seconds


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
            'zt_identity': self.data['ztIdentity'],
            'nics': self.data['nics'],
            'etcd_endpoint': self._etc_url
        }
        return j.sal_zos.traefik.get(**kwargs)
    @property
    def _etcd(self):
        return self.api.services.get(template_uid=ETCD_TEMPLATE_UID, name=self.data['etcdServerName'])
    @property
    def _etc_url(self):
        result = self._etcd.schedule_action('connection_info').wait(die=True).result
        return result['client_url']
        

    def node_port(self, port):
        return self._traefik_sal.container_port(port)

    def install(self):
        self.logger.info('Installing traefik %s' % self.name)

        traefik_sal = self._traefik_sal
        traefik_sal.deploy()
        self.data['ztIdentity'] = traefik_sal.zt_identity
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

    def add_virtual_host(self, domain, ip, port=80):
        self.state.check('actions', 'install', 'ok')
        self.logger.info('adding backend and frontend in etcd server')
        
        backend_name = "backend{}{}".format(ip.replace(".", ""), port)
        frontend_name = "frontend{}".format(domain.replace(".", ""))
        
        backend_key = "/traefik/backends/{}/servers/server1/url".format(backend_name)
        backend_value = "http://{}:{}".format(ip, port)
        self._etcd.schedule_action('insert_record', args={"key":backend_key, "value": backend_value}).wait(die=True)
        
        frontend_key1 = "/traefik/frontends/{}/backend".format(frontend_name)
        frontend_value1 = backend_name
        self._etcd.schedule_action('insert_record', args={"key":frontend_key1, "value": frontend_value1}).wait(die=True)
        
        frontend_key2 = "/traefik/frontends/{0}/routes/{0}/rule".format(frontend_name)
        frontend_value2 = "Host:{}".format(domain)
        self._etcd.schedule_action('insert_record', args={"key":frontend_key2, "value": frontend_value2}).wait(die=True)

        self.logger.info('successful')
