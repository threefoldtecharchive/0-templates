## template: github.com/threefoldtech/0-templates/web_gateway/0.0.1

### Description:
This template responsible for creating and managing a web gateway consisting of a coredns and traefik instance and an etcd cluster.

### Schema:

- `farmerIyoOrg`: the farmer to create the etcd cluster on
- `nrEtcds`: number of etcd instances in the etcd cluster
- `etcdPassword`: etcd cluster root user password. If not supplied, the template will generate it.
- `nics`: list of nics used for the traefik, coredns and etcd containers
- `publicNode`: the id of the node to deploy traefik and coredns on 
- `etcdConnectionInfo`: save the last etcd connection info

Nic:
- `id`: vxlan or vlan id or zerotier network id
- `type`: NicType enum specifying the nic type
- `hwaddr`: nic's macaddress
- `name`: nic name
- `ztClient`: zerotier_client service name to use to authorize. This service has to exist on the node.

NicType enum: 
- `default` 
- `vlan`
- `vxlan`
- `zerotier`

### Actions

- `install`: installs and starts traefik, coredns and the etcd cluster.
- `start`: start traefik, coredns and etcd cluster.
- `stop`: stop traefik, coredns and etcd cluster.
- `uninstall`: uninstall and delete traefik, coredns and etcd cluster.

### Usage example via the 0-robot DSL

```python
robot = j.clients.zrobot.robots['local']
args = {
    'nics': [{'name': 'ten', 'type': 'zerotier', 'ztClient':'zt', 'id': '1d719394044ed153'}],
    'farmerIyoOrg': 'farmer',
    'nrEtcds': 3,
    'publicNode': '124121421',
    }  
    
wg = robot.services.create('github.com/threefoldtech/0-templates/web_gateway/0.0.1', 'wg', data=args)
wg.schedule_action('install')
wg.schedule_action('start')
wg.schedule_action('stop')
```


### Usage example via the 0-robot CLI

To install web_gateway `wg`:

```yaml
services:
    - github.com/threefoldtech/0-templates/web_gateway/0.0.1__wg:
          nics:
            - name: 'ten'
            - id: 1d719394044ed153
            - ztClient: 'zt'
            - type: 'zerotier'
          farmerIyoIrg: 'farmer'
          nrEtcds: 3
          publicNode: 124121421
          
actions:
    - template: 'github.com/threefoldtech/0-templates/web_gateway/0.0.1'
      service: 'wg'
      actions: ['install']

```


To start  web_gateway `wg`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/web_gateway/0.0.1'
      service: 'wg'
      actions: ['start']

```


To stop  web_gateway `wg`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/web_gateway/0.0.1'
      service: 'wg'
      actions: ['stop']

```