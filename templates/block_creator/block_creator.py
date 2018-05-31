import os
import time
from random import shuffle

from js9 import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry
from zerorobot.template.state import StateCheckError

CONTAINER_TEMPLATE_UID = 'github.com/zero-os/0-templates/container/0.0.1'


class BlockCreator(TemplateBase):
    version = '0.0.1'
    template_name = 'block_creator'

    _DATA_DIR = '/mnt/data'
    _BACKUP_DIR = '/mnt/backups'

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        
        wallet_passphrase = self.data.get('walletPassphrase')
        if not wallet_passphrase:
            self.data['walletPassphrase'] = j.data.idgenerator.generateGUID()

        self.recurring_action('_monitor', 30)  # every 30 seconds
        self.recurring_action('peer_discovery', 300) # every 5 minutes


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
            'data_dir': self._DATA_DIR,
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

        # prepare persistent volume to mount into the container
        node_fs = self._node_sal.client.filesystem
        vol = os.path.join(fs.path, 'wallet')
        node_fs.mkdir(vol)

        vol_backup = os.path.join(fs.path, 'backups')
        node_fs.mkdir(vol_backup)

        mounts = [{
            'source': vol,
            'target': self._DATA_DIR
        },
        {
            'source': vol_backup,
            'target': self._BACKUP_DIR
        },
        ]

        # determine parent interface for macvlan
        parent_if = self.data.get("parentInterface")
        if not parent_if:
            candidates = list()
            for route in self._node_sal.client.ip.route.list():
                if route['gw']:
                    candidates.append(route)
            if not candidates:
                raise RuntimeError("Could not find interface for macvlan parent")
            elif len(candidates) > 1:
                raise RuntimeError("Found multiple eligible interfaces for macvlan parent: %s" % ", ".join(c['dev'] for c in candidates))
            parent_if = candidates[0]['dev']

        container_data = {
            'flist': self.data['tfchainFlist'],
            'node': self.data['node'],
            'nics': [{'type': 'macvlan', 'id': parent_if, 'name': 'stoffel', 'config': { 'dhcp': True }}],
            'mounts': mounts
        }
        return self.api.services.find_or_create(CONTAINER_TEMPLATE_UID, self._container_name, data=container_data)


    @retry((RuntimeError), tries=5, delay=2, backoff=2)
    def _wallet_init(self):
        """
        initialize the wallet with a new seed and password
        """
        try:
            self.state.check('wallet', 'init', 'ok')
            return
        except StateCheckError:
            pass

        self.logger.info('initializing wallet %s', self.name)
        self._client_sal.wallet_init()
        self.data['walletSeed'] = self._client_sal.recovery_seed
        self.state.set('wallet', 'init', 'ok')


    @retry((RuntimeError), tries=5, delay=2, backoff=2)
    def _wallet_unlock(self):
        """
        unlock the wallet, so it can start creating blocks and inspecting amount and addresses
        """
        try:
            self.state.check('wallet', 'unlock', 'ok')
            return
        except StateCheckError:
            pass
        self._client_sal.wallet_unlock()
        self.state.set('wallet', 'unlock', 'ok')


    def install(self):
        """
        Creating tfchain container with the provided flist, and configure mounts for datadirs
            'flist': TFCHAIN_FLIST,
        """
        self.logger.info('installing tfcaind %s', self.name)
        container = self._get_container()
        # ensure container is installed and running
        for action in ['install', 'start']:
            try:
                container.state.check('actions', action, 'ok')
            except StateCheckError:
                container.schedule_action(action).wait(die=True)

        self.state.set('actions', 'install', 'ok')


    def uninstall(self):
        """
        Remove the persistent volume of the wallet, and delete the container
        """
        try:
            self.stop()
            container = self.api.services.get(template_uid=CONTAINER_TEMPLATE_UID, name=self._container_name)
            container.delete()
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
        self.state.delete('wallet', 'unlock')
        self.state.delete('wallet', 'init')


    def start(self):
        """
        start both tfchain daemon and client
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Starting tfchaind %s', self.name)

        container = self._get_container()
        # ensure container is running
        try:
            container.state.check('actions', 'start', 'ok')
        except StateCheckError:
            container.schedule_action('start').wait(die=True)

        self._daemon_sal.start()
        self.state.set('status', 'running', 'ok')

        self._wallet_init()
        self._wallet_unlock()

        self.state.set('actions', 'start', 'ok')


    def stop(self):
        """
        stop tfchain daemon
        """
        self.logger.info('Stopping tfchain daemon %s', self.name)
        try:
            self._daemon_sal.stop()
            # force stop container
            container = self.api.services.get(template_uid=CONTAINER_TEMPLATE_UID, name=self._container_name)
            container.schedule_action('stop').wait(die=True)
        except (ServiceNotFoundError, LookupError):
            container = self._get_container()
            container.schedule_action('install').wait(die=True)      

        self.state.delete('status', 'running')
        self.state.delete('actions', 'start')
        self.state.delete('wallet', 'unlock')


    def upgrade(self, tfchainFlist=None):
        """upgrade the container with an updated flist
        this is done by stopping the container and respawn again with the updated flist

        tfchainFlist: If provided, the current used flist will be replaced with the specified one
        """
        # stop daemon
        self.stop()

        # update flist
        if tfchainFlist:
            self.data['tfchainFlist'] = tfchainFlist

        # delete and recreate the container
        container = self.api.services.get(template_uid=CONTAINER_TEMPLATE_UID, name=self._container_name)
        container.delete()
        container = self._get_container()
        container.schedule_action('install').wait(die=True)

        # Node does not need to open this port anymore
        self._node_sal.client.nft.drop_port(self.data['rpcPort'])

        # restart daemon in new container
        self.start()


    @retry((RuntimeError), tries=3, delay=2, backoff=2)
    def wallet_address(self):
        """
        load wallet address into the service's data
        """
        self.state.check('wallet', 'init', 'ok')

        if not self.data.get('walletAddr'):
            self.data['walletAddr'] = self._client_sal.wallet_address
        return self.data['walletAddr']


    @retry((RuntimeError), tries=3, delay=2, backoff=2)
    def wallet_amount(self):
        """
        return the amount of token in the wallet
        """
        self.state.check('wallet', 'unlock', 'ok')
        return self._client_sal.wallet_amount()


    @retry((RuntimeError), tries=3, delay=2, backoff=2)
    def consensus_stat(self):
        """
        return information about the state of consensus
        """
        self.state.check('status', 'running', 'ok')
        return self._client_sal.consensus_stat()


    @retry((RuntimeError), tries=3, delay=2, backoff=2)
    def report(self):
        """
        returns a full report containing the following fields:
        - wallet_status = string [locked/unlocked]
        - block_height = int
        - active_blockstakes = int
        - network = string [devnet/testnet/standard]
        - confirmed_balance = int
        - connected_peers = int
        - address = string
        """
        self.state.check('status', 'running', 'ok')
        report = self._client_sal.get_report()

        report["network"] = self.data["network"]
        return report


    def peer_discovery(self, link=None):
        """ Add new local peers 
        
            @link: network interface name
        """

        client = self._client_sal

        peers = client.discover_local_peers(link=link, port=self.data['rpcPort'])

        # shuffle list of peers
        shuffle(peers)

        # fetch list of connected peers
        connected_peers = [addr['netaddress'] for addr in client.gateway_stat()['peers']]
        
        # add first disconnected     peer
        for peer in peers:
            if peer not in connected_peers:
                [addr, port] = peer.split(':')
                client.add_peer(addr, port)
                return


    def _monitor(self):
        """ Unlock wallet if locked """
        self.state.check('actions', 'install', 'ok')
        self.state.check('actions', 'start', 'ok')
        try:
            if self._daemon_sal.is_running():
                self.state.set('status', 'running', 'ok')

                # get container status
                if self._client_sal.wallet_status() == 'locked':
                    self.state.delete('wallet', 'unlock')
                
                self._wallet_unlock()

                return
        except LookupError:
            # container not found, need to call start
            pass

        self.state.delete('status', 'running')
        self.state.delete('actions', 'start')
        self.state.delete('wallet', 'unlock')

        # force stop/delete container so install will create a new container
        try:
            container = self.api.services.get(template_uid=CONTAINER_TEMPLATE_UID, name=self._container_name)
            container.delete()
        except ServiceNotFoundError:
            pass

        self.install()
        self.start()
    

    def create_backup(self, name=''):
        """
        Create backup of the persistent files

        @name - name of the archive, if not given default name will be generated based on version and timestamp
        """
        self.state.check('status', 'running', 'ok')
        self._daemon_sal.stop()

        if not name:
            # generate backup name
            name = 'backup{}.tar.gz'.format(int(time.time()))

        cmd = 'tar -zcf {archive} {data} -P'.format(
            archive=os.path.join(self._BACKUP_DIR, name), data=self._DATA_DIR)

        try:
            result = self._container_sal.client.system(cmd).get()
            error_check(result, 'error occurred when creating backup')
        finally:
            self._daemon_sal.start()
            self._wallet_unlock()

    def list_backups(self):
        """ List all backups """

        self.state.check('status', 'running', 'ok')
        cmd = 'ls {}'.format(self._BACKUP_DIR)
        result = self._container_sal.client.system(cmd).get()
        error_check(result, 'error occurred when listing backups')

        parsed_output = result.stdout.split('\n')
        list_of_backups = [item for item in parsed_output if item]
        
        return list_of_backups

    def restore_backup(self, name):
        """
        Restore backup of the persistent files

        @name (required) - name of the archive; available archives can be listed with list_backups()
        """
        self.state.check('status', 'running', 'ok')
        self._daemon_sal.stop()
        cmd = 'tar -zxf {} -P'.format(os.path.join(self._BACKUP_DIR, name))

        try:
            result = self._container_sal.client.system(cmd).get()
            error_check(result, 'error occurred when restoring backup')
        finally:
            self._daemon_sal.start()
            self._wallet_unlock()


def error_check(result, message):
    """ Raise error if call wasn't successfull """

    if result.state != 'SUCCESS':
        err = '{}: {} \n {}'.format(message, result.stderr, result.data)
        raise RuntimeError(err)    
