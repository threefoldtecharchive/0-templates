from js9 import j
import os
import time
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError
from zerorobot.service_collection import ServiceNotFoundError


CONTAINER_TEMPLATE_UID = 'github.com/zero-os/0-templates/container/0.0.1'
TFCHAIN_FLIST = 'https://hub.gig.tech/tfchain/ubuntu-16.04-tfchain-latest.flist'


class BlockCreator(TemplateBase):
    version = '0.0.1'
    template_name = 'block_creator'

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self._tfchain_sal = None

        wallet_passphrase = self.data.get('walletPassphrase')
        if not wallet_passphrase:
            self.data['walletPassphrase'] = j.data.idgenerator.generateGUID()

        self.recurring_action('_monitor', 30)  # every 30 seconds

    @property
    def _node_sal(self):
        return j.clients.zero_os.sal.get_node(self.data['node'])

    @property
    def _container_sal(self):
        return self._node_sal.containers.get(self._container_name)

    @property
    def _container_name(self):
        return "container-%s" % self.guid

    @property
    def _daemon_sal(self):
        kwargs = {
            'name': self.name,
            'container': self._container_sal,
            'rpc_addr': '0.0.0.0:%s' % self.data['rpcPort'],
            'api_addr': 'localhost:%s' % self.data['apiPort'],
            'data_dir': '/mnt/data',
            'network': self.data.get('network', 'standard')
        }
        return j.clients.zero_os.sal.tfchain.daemon(**kwargs)

    @property
    def _client_sal(self):
        kwargs = {
            'name': self.name,
            'container': self._container_sal,
            'api_addr': 'localhost:%s' % self.data['apiPort'],
            'wallet_passphrase': self.data['walletPassphrase'],
        }
        return j.clients.zero_os.sal.tfchain.client(**kwargs)

    def _get_container(self):
        sp = self._node_sal.storagepools.get('zos-cache')
        try:
            fs = sp.get(self.guid)
        except ValueError:
            fs = sp.create(self.guid)

        ports = ['%s:%s' % (self.data['rpcPort'], self.data['rpcPort'])]

        # prepare persistant volume to mount into the container
        node_fs = self._node_sal.client.filesystem
        vol = os.path.join(fs.path, 'wallet')
        node_fs.mkdir(vol)
        mounts = [{
            'source': vol,
            'target': '/mnt/data'
        }]

        container_data = {
            'flist': TFCHAIN_FLIST,
            'node': self.data['node'],
            'nics': [{'type': 'default'}],
            'mounts': mounts,
            'ports': ports
        }

        return self.api.services.find_or_create(CONTAINER_TEMPLATE_UID, self._container_name, data=container_data)

    def install(self):
        """
        Creating tfchain container with the provided flist, and configure mounts for datadirs
            'flist': TFCHAIN_FLIST,
        """
        container = self._get_container()
        container.schedule_action('install').wait(die=True)
        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        """
        Remove the persistent volume of the wallet, and delete the container
        """
        try:
            self.stop()
        except (ServiceNotFoundError, LookupError):
            pass
        self.state.delete('status', 'running')

        try:
            # cleanup filesystem used by this robot
            sp = self._node_sal.storagepools.get('zos-cache')
            fs = sp.get(self.guid)
            fs.delete()
        except ValueError:
                # filesystem doesn't exist, nothing else to do
            pass

        self.state.delete('actions', 'install')
        self.state.delete('wallet', 'init')

    def start(self):
        """
        start both tfchain daemon and client
        """
        self.state.check('actions', 'install', 'ok')

        self.logger.info('Staring tfchaind {}'.format(self.name))
        container = self._get_container()
        container.schedule_action('start').wait(die=True)

        self.logger.info('Starting tfcaind %s' % self.name)
        self._daemon_sal.start()
        self.state.set('status', 'running', 'ok')

        try:
            self.state.check('wallet', 'init', 'ok')
        except StateCheckError:
            self.logger.info('initalizing wallet %s' % self.name)
            time.sleep(2)  # seems to be need for the daemon to be ready to init the wallet
            self._client_sal.wallet_init()
            self.data['walletSeed'] = self._client_sal.recovery_seed

        time.sleep(2)  # seems to be need for the daemon to be ready to unlock the wallet
        self._client_sal.wallet_unlock()

        self._node_sal.client.nft.open_port(self.data['rpcPort'])

        self.state.set('actions', 'start', 'ok')
        self.state.set('wallet', 'init', 'ok')

    def stop(self):
        """
        stop tfchain daemon
        """
        self.logger.info('Stopping tfchain daemon {}'.format(self.name))
        try:
            self._daemon_sal.stop()
            # force stop container
            container = self.api.services.get(template_uid=CONTAINER_TEMPLATE_UID, name=self._container_name)
            container.schedule_action('stop').wait(die=True)
            container.delete()
        except (ServiceNotFoundError, LookupError):
            # container is not found, good
            pass

        self._node_sal.client.nft.drop_port(self.data['rpcPort'])
        self.state.delete('status', 'running')
        self.state.delete('actions', 'start')

    def upgrade(self):
        """upgrade the container with an updated flist
        this is done by stopping the container and respawn again with the updated flist
        """
        # stop daemon
        self.stop()

        # restart daemon in new container
        self.start()

    def wallet_address(self):
        """
        load wallet address into the service's data
        """
        self.state.check('wallet', 'init', 'ok')

        if not self.data.get('walletAddr'):
            self.data['walletAddr'] = self._client_sal.wallet_address
        return self.data['walletAddr']

    def wallet_amount(self):
        """
        return the amount of token in the wallet
        """
        self.state.check('wallet', 'init', 'ok')
        return self._client_sal.wallet_amount()

    def consensus_stat(self):
        """
        return information about the state of consensus
        """
        self.state.check('status', 'running', 'ok')
        return self._client_sal.consensus_stat()

    def _monitor(self):
        self.state.check('actions', 'install', 'ok')
        self.state.check('actions', 'start', 'ok')

        try:
            if self._daemon_sal.is_running():
                self.state.set('status', 'running', 'ok')
                return
        except LookupError:
            # container not found, need to call start
            pass

        self.state.delete('status', 'running')

        # force stop/delete container so install will create a new container
        try:
            container = self.api.services.get(template_uid=CONTAINER_TEMPLATE_UID, name=self._container_name)
            container.delete()
        except ServiceNotFoundError:
            pass

        self.install()
        self.start()
