from js9 import j
import os
import time
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError
from zerorobot.service_collection import ServiceNotFoundError


CONTAINER_TEMPLATE_UID = 'github.com/zero-os/0-templates/container/0.0.1'
TFCHAIN_FLIST = 'https://hub.gig.tech/tfchain/ubuntu-16.04-tfchain-latest.flist'
EXPLORER_FLIST = 'https://hub.gig.tech/tfchain/caddy-explorer-latest.flist'


class Explorer(TemplateBase):
    version = '0.0.1'
    template_name = 'explorer'

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self._tfchain_sal = None
        self.recurring_action('_monitor', 30)  # every 30 seconds

    def validate(self):
        if not self.data.get('domain'):
            raise ValueError("domain need to be specified")

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
    def _explorer_sal(self):
        kwargs = {
            'name': self.name,
            'container': self._container_sal,
            'rpc_addr': '0.0.0.0:%s' % self.data['rpcPort'],
            'api_addr': 'localhost:%s' % self.data['apiPort'],
            'data_dir': '/mnt/data',
            'domain': self.data['domain'],
            'network': self.data.get('network', 'standard')
        }
        return j.clients.zero_os.sal.tfchain.explorer(**kwargs)

    def _get_container(self):
        sp = self._node_sal.storagepools.get('zos-cache')
        try:
            fs = sp.get(self.guid)
        except ValueError:
            fs = sp.create(self.guid)

        # prepare persistant volume to mount into the container
        node_fs = self._node_sal.client.filesystem
        vol = os.path.join(fs.path, 'explorer')
        node_fs.mkdir(vol)
        mounts = [
            {'source': vol,
             'target': '/mnt/data'},
            {'source': EXPLORER_FLIST,
             'target': '/mnt/explorer'}
        ]

        container_data = {
            'flist': TFCHAIN_FLIST,
            'node': self.data['node'],
            'nics': [{'type': 'default'}],
            'mounts': mounts,
            'ports': ['80:80', '443:443'],
        }

        return self.api.services.find_or_create(CONTAINER_TEMPLATE_UID, self._container_name, data=container_data)

    def install(self):
        """
        Creating tfchain container with the provided flist, and configure mounts for data dirs
        """
        self.logger.info("installing explorer %s", self.name)
        container = self._get_container()
        container.schedule_action('install').wait(die=True)
        self._explorer_sal.start()
        self.state.set('status', 'running', 'ok')
        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        """
        Remove the persistent volume of the explorer, and delete the container
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
        start both tfchain explorer and caddy
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Starting tfchaind and caddy (%s)', self.name)

        container = self._get_container()
        container.schedule_action('start').wait(die=True)

        self._explorer_sal.start()
        self.state.set('status', 'running', 'ok')

        self._node_sal.client.nft.open_port(self.data['rpcPort'])
        self._node_sal.client.nft.open_port(443)
        self._node_sal.client.nft.open_port(80)

        self.state.set('actions', 'start', 'ok')

    def stop(self):
        """
        stop tfchain explorer and caddy
        """
        self.logger.info('Stopping tfchain explorer and caddy (%s)', self.name)
        try:
            self._explorer_sal.stop()
            # force stop container
            container = self.api.services.get(template_uid=CONTAINER_TEMPLATE_UID, name=self._container_name)
            container.schedule_action('stop').wait(die=True)
            container.delete()
        except (ServiceNotFoundError, LookupError):
            # container is not found, good
            pass

        self._node_sal.client.nft.drop_port(self.data['rpcPort'])
        self._node_sal.client.nft.drop_port(443)
        self._node_sal.client.nft.drop_port(80)

        self.state.delete('status', 'running')
        self.state.delete('actions', 'start')

    def upgrade(self):
        """
        upgrade the container with an updated flist
        this is done by stopping the container and respawn again with the updated flist
        """
        self.stop()
        self.start()

    def consensus_stat(self):
        """
        return information about the state of consensus
        """
        self.state.check('status', 'running', 'ok')
        return self._explorer_sal.consensus_stat()

    def gateway_stat(self):
        """
        return information about the number of peers connected
        e.g: {'Active peers': '0', 'Address': '96.182.165.25'}
        """
        self.state.check('status', 'running', 'ok')
        return self._explorer_sal.gateway_stat()

    def _monitor(self):
        self.state.check('actions', 'install', 'ok')
        self.state.check('actions', 'start', 'ok')

        try:
            if self._explorer_sal.explorer.is_running():
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
