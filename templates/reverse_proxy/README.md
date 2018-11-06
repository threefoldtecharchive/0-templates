## template: github.com/threefoldtech/0-templates/reverse_proxy/0.0.1

### Description:
This template responsible for creating a reverse_proxy

### Schema:

- `webGateway`: the name of the web_gateway service to use. This service should already be installed.
- `domain`: the domain to expose.
- `servers`: the backend servers.


### Actions

- `install`: installs the service by putting all required keys and values in etcd
- `update_servers`: updates the backend servers in etcd
- `uninstall`: delete all keys from etcd


### Usage example via the 0-robot DSL

```python
robot = j.clients.zrobot.robots['local']
args = {
    'webGateway': 'wg',
    'domain': 'test.com',
    'servers': ['http://127.0.0.1:9000']}

rp = robot.services.create('github.com/threefoldtech/0-templates/reverse_proxy/0.0.1', 'rp', data=args)
rp.schedule_action('install')
rp.schedule_action('update_servers', args={'servers': ['http://127.0.0.1:8000']})
rp.schedule_action('uninstall')
```

### Usage example via the 0-robot CLI

To install reverse_proxy `rp`:

```yaml
services:
    - github.com/threefoldtech/0-templates/reverse_proxy/0.0.1__rp:
        webGateway: 'wg'
        domain: 'test.com'
        servers:
            - 'http://127.0.0.1:9000'

actions:
    - template: 'github.com/threefoldtech/0-templates/reverse_proxy/0.0.1'
      service: 'rp'
      actions: ['install']

```
