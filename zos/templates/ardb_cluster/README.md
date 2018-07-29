

## ARDB_Cluster

### Description:
This template is responsible for deploying a cluster of ARDBs


### Schema:
 - `instances`: number of ARDB instances to be deployed. It will deploy an instance or more on each node specified unless the number of instances specified is less the number of nodes; it will then deploy the number of instances, each on a seperate node.
 - `Nodes`: list of node names or service guids of nodes to deploy on

### Actions:
 - `install`: installs ARDB instances on specified nodes. Calls `configure`
 - `configure`: configures all ARDB instances
 - `start`: starts ARDB instances
 - `stop`: stops ARDB instances


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


actions:
    actions: ['install', 'start']
```


