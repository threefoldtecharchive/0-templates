## ARDB

### Description:
This template is responsible for deploying an ARDB instance


### Schema:
 - `node`: node name or service guid of node to deploy on
 - `data.directory`: data directory

### Actions:
 - `install`: installs ARDB on specified node. Calls `configure`
 - `configure`: configure ARDB
 - `start`: starts ARDB
 - `stop`: stops ARDB


```yaml
services:

    - github.com/jumpscale/0-robot/node/0.0.1__node:
        ...

    - github.com/jumpscale/0-robot/ardb/0.0.1__ardb:
        node: node
        data.directory: /mnt/db



actions:
    actions: ['install', 'start']
```



