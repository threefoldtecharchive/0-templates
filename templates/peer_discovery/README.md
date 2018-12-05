# template: github.com/threefoldtoken/0-templates/peer_discovery/0.0.1

## Description

Template is responsible for autodiscovering and adding new peers using [nmap](https://nmap.org/).

## Schema

* `node` - container name. **Required**.
* `container` - container name. **Required**.
* `rpcPort` - rpc port of tfchain daemon. Default to 23112
* `apiPort` - http port for tfchain client. Default to 23110
* `intervalScanNetwork` - interval between scanning network for new peers in seconds. Default to 86400 (24 hours).
* `intervalAddPeer` - interval between adding new peers in seconds. Default to 1800 (30 min).
* `discoveredPeers` - list of discovered peers. **Autofilled**.

## Actions

* `install` - install peer discovery service and schedule recurring actions `discover_peers` and `add_peer`.
* `discover_peers` - scan network for new peers and store in `self.data[discoveredPeers]`.
* `add_peer` - add the next peer.

## Usage examples via the 0-robot DSL

``` py
discovery = self.api.services.find_or_create(
    template_uid='github.com/threefoldtoken/0-templates/peer_discovery/0.0.1',
    service_name='peer_discovery',
    data = {
        'node': 'node_name',
        'container': 'container_name',
        'rpcPort': 23112,
        'apiPort': 23110,
        'intervalScanNetwork': 3600,
        'intervalAddPeer': 300,
    })
# install of the service will trigger recuring actions
# to scan network for peers and to add peers
discovery.schedule_action('install').wait(die=True)
```

## Usage examples via the 0-robot CLI

``` yaml
services:
    - github.com/threefoldtoken/0-templates/peer_discovery/0.0.1__discovery:
        node: 'node_name'
        container: 'container_name'
        rpcPort: 23112
        apiPort': 23110
        intervalScanNetwork: 3600
        intervalAddPeer: 300
actions:
    - service: discovery
      actions: ['install']
```
