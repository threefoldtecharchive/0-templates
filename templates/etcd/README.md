## template: github.com/threefoldtech/0-templates/etcd/0.0.1

### Description:
This is a node template responsible for managing [etcd](https://coreos.com/etcd/) server instance.

### Schema:

- `nics`: list of nics to create for the etcd container. Must contain at least one zerotier nic.
- `ztIdentity`: zerotier identity of the etcd container. This is set by the template.
- `token`: the token for the cluster
- `cluster`: a list of type Member. This is the list of the cluster members, it should contain the service itself too. If not supplied, it will default to just one member, the service itself.


Member:
- `name`: name of the etcd used in the config, this is the guid of the service.
- `address`: peer address of the etcd


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

- `install`: creates the etcd container and makes sure it is assigned a zerotier ip but doesn't start the etcd process. That way if you want to create a cluster, you can install all the relevant etcd services then update them all with all their urls before starting.
- `start`: start etcd with the right cluster configuration.
- `stop`: stop the etcd process.
- `uninstall`: stop the etcd process and remove the container.
- `connection_info`: returns both the client and peer url
- `update_cluster`: updates the cluster value in self.data. This should be used to update the service with info about all the members of this cluster.
- `insert_record`: inserts a key/value in etcd
- `get_record`: retrieves a value of a key in etcd
- `delete_record`: delete record by key from etcd server



### Usage example via the 0-robot DSL

```python
robot = j.clients.zrobot.robots['local']
args = {
    'nics': [{'name': 'ten', 'type': 'zerotier', 'ztClient':'zt', 'id': '1d719394044ed153'}],
    'token': 'token-one'
    }  
    
etcd = robot.services.create('github.com/threefoldtech/0-templates/etcd/0.0.1', 'etcd1', data=args)
etcd.schedule_action('install')
etcd.schedule_action('start')
etcd.schedule_action('insert_record', args={'key': 'one', 'value':'one'})
etcd.schedule_action('delete_record', args={'key': 'one'})
etcd.schedule_action('stop')
```


### Usage example via the 0-robot CLI

To install etcd `etcd1`:

```yaml
services:
    - github.com/threefoldtech/0-templates/etcd/0.0.1__etcd1:
          token: 'token-one'
          nics:
            - name: 'ten'
            - id: 1d719394044ed153
            - ztClient: 'zt'
            - type: 'zerotier'
          
actions:
    - template: 'github.com/threefoldtech/0-templates/etcd/0.0.1'
      service: 'etcd1'
      actions: ['install']

```


To start  etcd `etcd1`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/etcd/0.0.1'
      service: 'etcd1'
      actions: ['start']

```


To stop  etcd `etcd1`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/etcd/0.0.1'
      service: 'etcd1'
      actions: ['stop']

```