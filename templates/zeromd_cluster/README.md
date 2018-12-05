

## ZeroMD_Cluster

### Description:
This template is responsible for deploying a cluster of 0-metadatastors


### Schema:
 - `ardb.cluster`: name or service guid of the ARDB cluster backend.
 - `instances`: number of 0-metada instances to be deployed. It will deploy an instance or more on each node specified unless the number of instances specified is less the number of nodes; it will then deploy the number of instances, each on a seperate node.
 - `Nodes`: list of node names or service guids of nodes to deploy on.

### Actions:
 - `install`: installs 0-metadata instances on specified nodes. Calls `configure`.
 - `configure`: configures all 0-metadata instances to connect to ARDB cluster.
 - `start`: starts 0-metadata instances.
 - `stop`: stops 0-metadata instances.


```yaml
services:

    - github.com/jumpscale/0-robot/node/0.0.1__node1:
        ...

    - github.com/jumpscale/0-robot/node/0.0.1__node2:
        ... 

    - github.com/jumpscale/0-robot/node/0.0.1__node3:
        ...

    - github.com/jumpscale/0-robot/node/0.0.1__node4:
        ...

    - github.com/jumpscale/0-robot/node/0.0.1__node5:
        ...

    - github.com/jumpscale/0-robot/ardb_cluster/0.0.1__ardbcluster:
        instances: 4
        nodes:         
          - node1
          - node2
          - node3

    - github.com/jumpscale/0-robot/zeromd_cluster/0.0.1__zeromdcluster:
        ardbcluster: ardbcluster
        instances: 4
        nodes:         
          - node1
          - node4
          - node5


actions:
    actions: ['install', 'start']
```



