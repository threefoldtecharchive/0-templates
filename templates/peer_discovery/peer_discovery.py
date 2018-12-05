from random import shuffle

from Jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError

class PeerDiscovery(TemplateBase):
    version = '0.0.1'
    template_name = 'peer_discovery'

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)

    def validate(self):
        for key in ['node', 'container', 'rpcPort', 'apiPort', 'intervalScanNetwork', 'intervalAddPeer']:
            if not self.data[key]:
                raise ValueError('"{}" is required'.format(key))

    def install(self):
        """
        Install peer_discovery
        """
        try:
            self.state.check('actions', 'install', 'ok')
            return
        except StateCheckError:
            pass

        # schedule peer discovery
        self.recurring_action('discover_peers', self.data['intervalScanNetwork'])

        # schedule adding peers
        self.recurring_action('add_peer', self.data['intervalAddPeer'])

        self.state.set('actions', 'install', 'ok')

    @property
    def _node_sal(self):
        return j.clients.zero_os.sal.get_node(self.data['node'])


    @property
    def _container_sal(self):
        return self._node_sal.containers.get(self.data['container'])


    @property
    def _client_sal(self):
        kwargs = {
            'name': self.name,
            'container': self._container_sal,
            'api_addr': 'localhost:%s' % self.data['apiPort'],
            'wallet_passphrase': "",
        }
        return j.clients.zero_os.sal.tfchain.client(**kwargs)


    def discover_peers(self, link=None):
        """ Add new local peers 

            @link: network interface name
        """
        self.logger.info('start network scanning')
        client = self._client_sal

        peers = client.discover_local_peers(link=link, port=self.data['rpcPort'])
        # shuffle list of peers
        shuffle(peers)

        # fetch list of connected peers
        connected_peers = [addr['netaddress'] for addr in client.gateway_stat()['peers']]
        
        # add update list of discovered peers
        self.data['discoveredPeers'] = []
        for peer in peers:
            if peer not in connected_peers:
                self.data['discoveredPeers'].append(peer)


    def add_peer(self):
        """ Add a peer from list of discovered peers """

        if self.data['discoveredPeers']:
            peer = self.data['discoveredPeers'].pop(0)
            [addr, port] = peer.split(':')
            self._client_sal.add_peer(addr, port)


