from random import shuffle

from js9 import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError

class BlockCreator(TemplateBase):
    version = '0.0.1'
    template_name = 'peer_discovery'

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        
        if not self.data['interval']:
            # if interval is not given, set interval to 12 hours
            self.data['interval'] = 3600*12
        
        # scheduler peer discovery
        self.recurring_action('discover_peers', self.data['interval'])


    @property
    def _node_sal(self):
        return j.clients.zero_os.sal.get_node(self.data['node'])


    @property
    def _container_sal(self):
        return self._node_sal.containers.get(self._container_name)


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

        client = self._client_sal

        peers = client.discover_local_peers(link=link, port=self.data['rpcPort'])

        # shuffle list of peers
        shuffle(peers)

        # fetch list of connected peers
        connected_peers = [addr['netaddress'] for addr in client.gateway_stat()['peers']]
        
        # add first disconnected peer
        for peer in peers:
            if peer not in connected_peers:
                [addr, port] = peer.split(':')
                client.add_peer(addr, port)
                return

    
