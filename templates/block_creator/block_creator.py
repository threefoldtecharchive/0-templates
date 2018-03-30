from js9 import j
import os
import time
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError
from zerorobot.service_collection import ServiceNotFoundError


CONTAINER_TEMPLATE_UID = 'github.com/zero-os/0-templates/container/0.0.1'
TFCHAIN_FLIST = 'https://hub.gig.tech/lee/ubuntu-16.04-tfchain-0.6.0.flist'


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
    def node_sal(self):
        return j.clients.zero_os.sal.get_node(self.data['node'])

    @property
    def container_sal(self):
        return self.node_sal.containers.get(self._container_name)

    @property
    def _container_name(self):
        return "container-%s" % self.guid

    @property
    def tfchain_sal(self):
        if self._tfchain_sal is None:
            kwargs = {
                'name': self.name,
                'container': self.container_sal,
                'rpc_addr': '0.0.0.0:%s' % self.data['rpcPort'],
                'api_addr': 'localhost:%s' % self.data['apiPort'],
                'wallet_passphrase': self.data['walletPassphrase'],
                'data_dir': '/mnt/data',
            }

            self._tfchain_sal = j.clients.zero_os.sal.get_tfchain(**kwargs)
        return self._tfchain_sal

    def _get_container(self):
        sp = self.node_sal.storagepools.get('zos-cache')
        try:
            fs = sp.get(self.guid)
        except ValueError:
            fs = sp.create(self.guid)

        # prepare persistant volume to mount into the container
        node_fs = self.node_sal.client.filesystem
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
            contservice = self.api.services.get(name=self._container_name)
            contservice.schedule_action('uninstall').wait(die=True)
            contservice.delete()
        except (ServiceNotFoundError, LookupError):
            pass
        self.state.delete('status', 'running')

        try:
            # cleanup filesystem used by this robot
            sp = self.node_sal.storagepools.get('zos-cache')
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
        self.tfchain_sal.daemon.start()
        self.state.set('status', 'running', 'ok')

        try:
            self.state.check('wallet', 'init', 'ok')
        except StateCheckError:
            self.logger.info('initalizing wallet %s' % self.name)
            time.sleep(2)  # seems to be need for the daemon to be ready to init the wallet
            self.tfchain_sal.client.wallet_init()
            self.data['walletSeed'] = self.tfchain_sal.client.recovery_seed

        time.sleep(2)  # seems to be need for the daemon to be ready to unlock the wallet
        self.tfchain_sal.client.wallet_unlock()
        self.state.set('actions', 'start', 'ok')
        self.state.set('wallet', 'init', 'ok')

    def stop(self):
        """
        stop tfchain daemon
        """
        self.logger.info('Stopping tfchain daemon {}'.format(self.name))
        try:
            self.tfchain_sal.daemon.stop()
        except (ServiceNotFoundError, LookupError):
            # container is not found, good
            pass
        self.state.delete('status', 'running')
        self.state.delete('actions', 'start')

    def upgrade(self):
        """upgrade the container with an updated flist
        this is done by stopping the container and respawn again with the updated flist
        """
        self.state.check('actions', 'install', 'ok')
        container = self.api.services.get(template_uid=CONTAINER_TEMPLATE_UID, name=self._container_name)
        container.schedule_action('stop').wait()
        self.start()

    def wallet_address(self):
        """
        load wallet address into the service's data
        """
        self.state.check('wallet', 'init', 'ok')

        if not self.data.get('walletAddr'):
            self.data['walletAddr'] = self.tfchain_sal.client.wallet_address
        return self.data['walletAddr']

    def wallet_amount(self):
        """
        return the amount of token in the wallet
        """
        self.state.check('wallet', 'init', 'ok')
        cmd = '/tfchainc --addr %s wallet' % self.tfchain_sal.client.addr
        result = self.tfchain_sal.client.container.client.system(cmd).get()
        if result.state != 'SUCCESS':
            raise RuntimeError("Could not unlock wallet: %s" % result.stderr.splitlines()[-1])

        args = {}
        for line in result.stdout.splitlines()[2:]:
            k, v = line.split(':')
            k = k.strip()
            v = v.strip()
            args[k] = v
        return args

    def consensus_stat(self):
        """
        return information about the state of consensus
        """
        self.state.check('status', 'running', 'ok')
        return self.tfchain_sal.client.consensus_stat()

    def _monitor(self):
        self.state.check('actions', 'install', 'ok')
        self.state.check('actions', 'start', 'ok')

        prev_timeout = self.tfchain_sal.client.container.client.timeout
        try:
            self.tfchain_sal.client.container.client.timeout = 10
            if self.tfchain_sal.daemon.is_running():
                self.state.set('status', 'running', 'ok')
                return

            self.state.delete('status', 'running')
            self.start()
        finally:
            self.tfchain_sal.client.container.client.timeout = prev_timeout