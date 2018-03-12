from js9 import j

from zerorobot.template.base import TemplateBase

CONTAINER_TEMPLATE_UID = 'github.com/zero-os/0-templates/container/0.0.1'
TFCHAIN_FLIST = 'https://hub.gig.tech/lee/ubuntu-16.04-tfchain-v0.1.0.flist'


class BlockCreator(TemplateBase):
    version = '0.0.1'
    template_name = 'block_creator'

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        if bool(self.data.get('nodeMountPoint')) != bool(self.data['containerMountPoint']):
            raise ValueError('nodeMountPoint and containerMountPoint must either both be defined or both be none.')

        self._rivine_sal = None

    @property
    def node_sal(self):
        return j.clients.zero_os.sal.node_get(self.data['node'])

    @property
    def container_sal(self):
        return self.node_sal.containers.get(self.data['container'])

    @property
    def rivine_sal(self):
        if self._rivine_sal is None:
            kwargs = {
                'name': self.name,
                'container': self.container_sal,
                'rpc_addr': '0.0.0.0:%s' % self.data['rpcPort'],
                'api_addr': 'localhost:%s' % self.data['apiPort'],
            }
            self._rivine_sal = j.clients.zero_os.sal.rivine_get(**kwargs)
        return self._rivine_sal

    def install(self):
        """
        Creating tfchain container with the provided flist, and configure mounts for datadirs
        """
        mounts = {}
        if self.data['nodeMountPoint'] and self.data['containerMountPoint']:
            mounts = {self.data['nodeMountPoint']: self.data['containerMountPoint']}

        container_data = {
            'flist': TFCHAIN_FLIST,
            'mounts': mounts,
            'node': self.data['node'],
            'hostNetworking': True,
        }

        self.data['container'] = 'container_%s' % self.name
        container = self.api.services.create(CONTAINER_TEMPLATE_UID, self.data['container'], data=container_data)
        container.schedule_action('install').wait()

        self.state.set('actions', 'install', 'ok')

    def start(self):
        """
        start both tfchain daemon and client
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Staring tfchaind {}'.format(self.name))
        container = self.api.services.get(template_uid=CONTAINER_TEMPLATE_UID, name=self.data['container'])
        container.schedule_action('start').wait()

        self.rivine_sal.daemon.start()

        self.rivine_sal.client.wallet_init()

        self.data['walletSeed'] = self.rivine_sal.client.recovery_seed
        self.data['walletPassphrase'] = self.rivine_sal.client.wallet_password
        self.state.set('actions', 'start', 'ok')

    def stop(self):
        """
        stop tfchain daemon
        """
        self.state.check('actions', 'start', 'ok')
        self.logger.info('Stopping rivine daemon {}'.format(self.name))
        self.rivine_sal.daemon.stop()
        self.state.delete('actions', 'start')
