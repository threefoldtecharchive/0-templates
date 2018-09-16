from jumpscale import j

from zerorobot.template.base import TemplateBase


MINIO_FLIST = 'https://hub.gig.tech/gig-official-apps/minio.flist'
META_DIR = '/bin/zerostor_meta'
NODE_CLIENT = 'local'


class Minio(TemplateBase):

    version = '0.0.1'
    template_name = "minio"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.add_delete_callback(self.uninstall)
        self.recurring_action('_monitor', 30)  # every 30 seconds

    def validate(self):
        self.state.delete('status', 'running')
        for param in ['zerodbs', 'namespace', 'login', 'password']:
            if not self.data.get(param):
                raise ValueError("parameter '%s' not valid: %s" % (param, str(self.data[param])))

    def _monitor(self):
        self.logger.info('Monitor minio %s' % self.name)
        self.state.check('actions', 'install', 'ok')
        self.state.check('actions', 'start', 'ok')

        if not self._minio_sal.is_running():
            self.state.delete('status', 'running')
            self.start()
            if self._minio_sal.is_running():
                self.state.set('status', 'running', 'ok')
        else:
            self.state.set('status', 'running', 'ok')

    @property
    def node_sal(self):
        return j.clients.zos.get(NODE_CLIENT)

    @property
    def _minio_sal(self):
        kwargs = {
            'name': self.name,
            'node': self.node_sal,
            'namespace': self.data['namespace'],
            'namespace_secret': self.data['nsSecret'],
            'zdbs': self.data['zerodbs'],
            'node_port': self.data['listenPort'],
            'private_key': self.data['privateKey'],
            'login': self.data['login'],
            'password': self.data['password'],
            'meta_private_key': self.data['metaPrivateKey'],
            'nr_datashards': self.data['dataShard'],
            'nr_parityshards': self.data['parityShard']
        }
        return j.sal_zos.minio.get(**kwargs)

    def node_port(self):
        return self.data['node_port']

    def install(self):
        self.logger.info('Installing minio %s' % self.name)
        minio_sal = self._minio_sal

        self.data['node_port'] = minio_sal.node_port
        self.state.set('actions', 'install', 'ok')

    def start(self):
        """
        start minio server
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Starting minio %s' % self.name)
        self._minio_sal.start()
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
        self.state.delete('actions', 'install')
        self.state.delete('status', 'running')

    def update_zerodbs(self, zerodbs):
        self.data['zerodbs'] = zerodbs
