## ZeroMD
### Description

This template is responsible for deploying a 0-metadatastor (see: [0-metadata](https://github.com/zero-os/0-metadata))

### Schema:
 - `node`: node to install the 0-metadata on.
 - `port`: port for 0-metadata to run on.
 - `ardb.cluster`: name or service guid of ARDB cluster.

### Actions:
 - `install`: installs 0-metadata on configured node. Calls `configure`.
 - `configure`: configures 0-metadata to connect to ARDB cluster.
 - `start`: starts 0-metadata on configured port.
 - `stop`: stops 0-metadata.

### Blueprint example:
```yaml
services:
    - github.com/jumpscale/0-robot/node/0.0.1__node1:
        ...

    - github.com/jumpscale/0-robot/node/0.0.1__node2:
        ... 

    - github.com/jumpscale/0-robot/node/0.0.1__node3:
        ...

    - github.com/jumpscale/0-robot/ardb_cluster/0.0.1__ardbcluster:
        instances: 4
        nodes:         
          - node1
          - node2
          - node3

    - github.com/threefoldtech/0-templates/zeromd/0.0.1__zeromd:
        node: node
        port: 666
        ardb.cluster: 'ardbcluster'


actions:
    actions: ['install', 'start']
```

