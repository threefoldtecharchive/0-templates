## template: github.com/threefoldtech/0-templates/etcd_cluster/0.0.1

### Description:
This template responsible for creating and managing an [etcd](https://coreos.com/etcd/) cluster.

### Schema:

- `farmerIyoOrg`: the farmer to create the etcd instances on
- `nrEtcds`: number of etcd instances in this cluster
- `etcds`:  a list of type Etcd. This is set by the template to keep track of deployed etcds.
- `nics`: list of nics to create for the etcd container. Must contain at least one zerotier nic.
- `token`: the token for the cluster. If not supplied, the template will generate one.
- `password`: password to be used to create root user. If not supplied, the template will generate one.
- `clusterConnections`: the cluster connection string used in the etcd configuration of all instances. This is set by the template.

Etcd:
- `name`: etcd instance service name
- `node`: node id of the node this instance is created on
- `url`: node zrobot url

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

- `install`: creates all required etcds, updates them with the right cluster info, starts the etcds, then enables auth and prepares it for traefik.
- `start`: start all etcds.
- `stop`: stop all etcds.
- `uninstall`: uninstall all etcd instances
- `connection_info`: returns cluster connection info

### Usage example via the 0-robot DSL

```python
robot = j.clients.zrobot.robots['local']
args = {
    'nics': [{'name': 'ten', 'type': 'zerotier', 'ztClient':'zt', 'id': '1d719394044ed153'}],
    'token': 'token-one',
    'farmerIyoOrg': 'farmer',
    'nrEtcds': 3,
    }  
    
etcd = robot.services.create('github.com/threefoldtech/0-templates/etcd_cluster/0.0.1', 'etcd1', data=args)
etcd.schedule_action('install')
etcd.schedule_action('start')
etcd.schedule_action('stop')
```


### Usage example via the 0-robot CLI

To install etcd_cluster `etcd1`:

```yaml
services:
    - github.com/threefoldtech/0-templates/etcd_cluster/0.0.1__etcd1:
          token: 'token-one'
          nics:
            - name: 'ten'
            - id: 1d719394044ed153
            - ztClient: 'zt'
            - type: 'zerotier'
          farmerIyoIrg: 'farmer'
          nrEtcds: 3
          
actions:
    - template: 'github.com/threefoldtech/0-templates/etcd_cluster/0.0.1'
      service: 'etcd1'
      actions: ['install']

```


To start  etcd_cluster `etcd1`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/etcd_cluster/0.0.1'
      service: 'etcd1'
      actions: ['start']

```


To stop  etcd_cluster `etcd1`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/etcd_cluster/0.0.1'
      service: 'etcd1'
      actions: ['stop']

```
