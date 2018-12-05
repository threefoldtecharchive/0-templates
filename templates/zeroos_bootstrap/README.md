## template: github.com/threefoldtech/0-templates/zeroos_bootstrap/0.0.1

### Description:
This template is responsible for bootstraping zero-os nodes.

### Schema:

- `zerotierClient`: the instance name of the zerotier client to use.
- `zerotierNetID`: zerotier netowrok ID to use for discovering nodes.
- `wipeDisks`: boolean indicating whether the node disks should be wiped or not.
- `redisPassword`: jwt token used as password when connecting to the node

### Actions:
- `bootstrap`: recurring action that runs every 10 seconds. It checks if there are any nodes in the zerotier network and authorizes these nodes.
- `delete`: unauthorizes a node from the zerotier network.

    arguments:
    - `redis_addr`: the redis address of the node to remove.


```yaml
services:
    - github.com/threefoldtech/0-templates/zeroos_bootstrap/0.0.1__bootstrap:
          zerotierClient: 'main'
          zerotierNetID: '12ac4a1e7122ed7a'
          redisPassword: <jwt_token>

```
