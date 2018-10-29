from jumpscale import j

from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError

PORT_MANAGER_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/node_port_manager/0.0.1'

NODE_CLIENT = 'local'


class Minio(TemplateBase):

    version = '0.0.1'
    template_name = "minio"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self._node_sal = j.clients.zos.get(NODE_CLIENT)
        self.add_delete_callback(self.uninstall)
        self.recurring_action('_monitor', 30)  # every 30 seconds

    def validate(self):
        self.state.delete('status', 'running')
        for param in ['zerodbs', 'namespace', 'login', 'password']:
            if not self.data.get(param):
                raise ValueError("parameter '%s' not valid: %s" % (param, str(self.data[param])))

    def _monitor(self):
        self.logger.info('Monitor minio %s' % self.name)
        try:
            self.state.check('actions', 'install', 'ok')
            self.state.check('actions', 'start', 'ok')
        except StateCheckError:
            return

        if not self._minio_sal.is_running():
            self.state.delete('status', 'running')
            self.start()
            if self._minio_sal.is_running():
                self.state.set('status', 'running', 'ok')
        else:
            self.state.set('status', 'running', 'ok')

    @property
    def _minio_sal(self):
        kwargs = {
            'name': self.name,
            'node': self._node_sal,
            'namespace': self.data['namespace'],
            'namespace_secret': self.data['nsSecret'],
            'zdbs': self.data['zerodbs'],
            'private_key': self.data['privateKey'],
            'login': self.data['login'],
            'password': self.data['password'],
            'meta_private_key': self.data['metaPrivateKey'],
            'nr_datashards': self.data['dataShard'],
            'nr_parityshards': self.data['parityShard'],
            'tlog_namespace': self.data.get('tlog').get('namespace'),
            'tlog_address': self.data.get('tlog').get('address'),
            'master_namespace': self.data.get('master').get('namespace'),
            'master_address': self.data.get('master').get('address'),
            'block_size': self.data['blockSize'],
            'node_port': self.data['nodePort'],
        }
        return j.sal_zos.minio.get(**kwargs)

    def node_port(self):
        self.state.check('actions', 'install', 'ok')
        return self.data['nodePort']

    def install(self):
        self.logger.info('Installing minio %s' % self.name)
        self._reserve_port()
        self.state.set('actions', 'install', 'ok')

    def start(self):
        """
        start minio server
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Starting minio %s' % self.name)
        minio_sal = self._minio_sal
        minio_sal.start()
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def stop(self):
        """
        stop minio server
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Stopping minio %s' % self.name)
        self._minio_sal.stop()
        self.state.delete('actions', 'start')
        self.state.delete('status', 'running')

    def uninstall(self):
        self.logger.info('Uninstalling minio %s' % self.name)
        self._minio_sal.destroy()

        self._release_port()

        self.state.delete('actions', 'install')
        self.state.delete('status', 'running')

    def update_zerodbs(self, zerodbs):
        self.data['zerodbs'] = zerodbs
        # if minio is running and we update the config, tell it to reload the config
        minio_sal = self._minio_sal
        if minio_sal.is_running():
            minio_sal.create_config()
            minio_sal.reload()

    def update_tlog(self, namespace, address):
        self.data['tlog'] = {
            'namespace': namespace,
            'address': address
        }
        # if minio is running and we update the config, tell it to reload the config
        minio_sal = self._minio_sal
        if minio_sal.is_running():
            minio_sal.create_config()
            minio_sal.reload()

    def update_master(self, namespace, address):
        self.data['master'] = {
            'namespace': namespace,
            'address': address
        }
        # if minio is running and we update the config, tell it to reload the config
        minio_sal = self._minio_sal
        if minio_sal.is_running():
            minio_sal.create_config()
            minio_sal.reload()

    def _reserve_port(self):
        port_mgr = self.api.services.get(template_uid=PORT_MANAGER_TEMPLATE_UID, name='_port_manager')
        self.data['nodePort'] = port_mgr.schedule_action("reserve", {"service_guid": self.guid, 'n': 1}).wait(die=True).result[0]

    def _release_port(self):
        port_mgr = self.api.services.get(template_uid=PORT_MANAGER_TEMPLATE_UID, name='_port_manager')
        port_mgr.schedule_action("release", {"service_guid": self.guid, 'ports': [self.data['nodePort']]})
