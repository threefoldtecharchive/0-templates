## template: github.com/threefoldtech/0-templates/traefik/0.0.1

### Description:
This is a node template responsible for managing [traefik](https://docs.traefik.io/) server instance.

### Schema:
- `etcdServerName`: the name of etcd server that's created to get ip of it
- `nics`: list of nics to create for the traefik container. Must contain at least one zerotier nic.
- `ztIdentity`: zerotier identity of the traefik container. This is set by the template.

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

- `install`: creates the traefik container and makes sure it is assigned a zerotier ip but doesn't start the traefik process.
- `start`: start traefik service and create traefik config .
- `stop`: stop the traefik process.
- `uninstall`: stop the traefik process and remove the container.
- `add_virtual_host`: inserts a frontend/backend in Etcd service.
- `remove_virtual_host`: delete frontend only from Etcd service


### Usage example via the 0-robot DSL

```python
robot = j.clients.zrobot.robots['local']
args = {
    'nics': [{'name': 'ten', 'type': 'zerotier', 'ztClient':'zt', 'id': '1d719394044ed153'}],
    'etcdServerName': 'Etcd server name that created'
    }  
    
traefik = robot.services.create('github.com/threefoldtech/0-templates/traefik/0.0.1', 'traefik1', data=args)
traefik.schedule_action('install')
traefik.schedule_action('start')
traefik.schedule_action('add_virtual_host', args={'domain': 'bola_test.com', 'ip':'10.147.17.198'})
traefik.schedule_action('remove_virtual_host', args={'domain': 'bola_test.com'})
traefik.schedule_action('stop')
traefik.schedule_action('uninstall')
```


### Usage example via the 0-robot CLI

To install traefik `traefik1`:

```yaml
services:
    - github.com/threefoldtech/0-templates/traefik/0.0.1__traefik1:
          etcdServerName: 'Etcd_server_name'
          nics:
            - name: 'ten'
            - id: 1d719394044ed153
            - ztClient: 'zt'
            - type: 'zerotier'
          
actions:
    - template: 'github.com/threefoldtech/0-templates/traefik/0.0.1'
      service: 'traefik'
      actions: ['install']

```


To start  traefik `traefik1`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/traefik/0.0.1'
      service: 'traefik1'
      actions: ['start']

```


To stop  traefik `traefik1`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/traefik/0.0.1'
      service: 'traefik1'
      actions: ['stop']

```