from js9 import j

from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError


CONTAINER_TEMPLATE_UID = 'github.com/zero-os/0-templates/container/0.0.1'
# TFCHAIN_FLIST = 'https://hub.gig.tech/khaledkbadr/tfchain-ubuntu.flist'
TFCHAIN_FLIST = 'http://192.168.20.132:8080/khaledkbadr/tfchain-ubuntu.flist'


class BlockCreator(TemplateBase):
    version = '0.0.1'
    template_name = 'block_creator'

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self._tfchain_sal = None

        self.recurring_action('_monitor', 300)  # every 300 seconds

    def validate(self):
        if bool(self.data.get('nodeMountPoint')) != bool(self.data['containerMountPoint']):
            raise ValueError('nodeMountPoint and containerMountPoint must either both be defined or both be none.')

        if not bool(self.data.get('walletPassphrase')):
            raise ValueError('walletPassphrase must be defined.')

    @property
    def node_sal(self):
        return j.clients.zero_os.sal.get_node(self.data['node'])

    @property
    def container_sal(self):
        return self.node_sal.containers.get(self.data['container'])

    @property
    def tchain_sal(self):
        if self._tfchain_sal is None:
            kwargs = {
                'name': self.name,
                'container': self.container_sal,
                'rpc_addr': '0.0.0.0:%s' % self.data['rpcPort'],
                'api_addr': 'localhost:%s' % self.data['apiPort'],
                'wallet_passphrase': self.data['walletPassphrase'],
            }

            if self.data['nodeMountPoint'] and self.data['containerMountPoint']:
                kwargs['data_dir'] = self.data['containerMountPoint']

            self._tfchain_sal = j.clients.zero_os.sal.get_tfchain(**kwargs)
        return self._tfchain_sal

    def install(self):
        """
        Creating tfchain container with the provided flist, and configure mounts for datadirs
            'flist': TFCHAIN_FLIST,
        """
        mounts = []
        if self.data['nodeMountPoint'] and self.data['containerMountPoint']:
            mounts = [{'source': self.data['nodeMountPoint'], 'target': self.data['containerMountPoint']}]

        container_data = {
            'flist': TFCHAIN_FLIST,
            'node': self.data['node'],
            'hostNetworking': True,
            'mounts': mounts,
        }

        self.data['container'] = 'container_%s' % self.name
        container = self.api.services.create(
            CONTAINER_TEMPLATE_UID, self.data['container'], data=container_data)
        container.schedule_action('install').wait()
        self.state.set('actions', 'install', 'ok')

    def start(self):
        """
        start both tfchain daemon and client
        """
        self.state.check('actions', 'install', 'ok')

        self.logger.info('Staring tfchaind {}'.format(self.name))
        container = self.api.services.get(
            template_uid=CONTAINER_TEMPLATE_UID, name=self.data['container'])
        container.schedule_action('start').wait()

        self.logger.info('Starting tfcaind %s' % self.name)
        self.tchain_sal.daemon.start()
        self.state.set('status', 'running', 'ok')

        try:
            self.state.check('wallet', 'init', 'ok')
        except:
            self.logger.info('initalizing wallet %s' % self.name)
            self.tchain_sal.client.wallet_init()
            self.tchain_sal.client.wallet_unlock()
            self.data['walletSeed'] = self.tchain_sal.client.recovery_seed

        self.state.set('actions', 'start', 'ok')
        self.state.set('wallet', 'init', 'ok')

    def stop(self):
        """
        stop tfchain daemon
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Stopping tfchain daemon {}'.format(self.name))
        self.tchain_sal.daemon.stop()
        self.state.delete('status', 'running')

    def upgrade(self):
        """upgrade the container with an updated flist
        this is done by stopping the container and respawn again with the updated flist
        """
        self.state.check('actions', 'install', 'ok')
        container = self.api.services.get(template_uid=CONTAINER_TEMPLATE_UID, name=self.data['container'])
        container.schedule_action('stop').wait()
        self.start()

    def wallet_address(self):
        """load wallet address into the service's data
        """
        self.data['walletAddr'] = self.tchain_sal.client.wallet_address

    def _monitor(self):
        if self.tchain_sal.daemon.is_running():
            return

        self.state.delete('status', 'running')

        try:
            self.state.check('status', 'running', 'ok')
            self.start()
        except StateCheckError:
            pass
