## template: github.com/threefoldtech/0-templates/corednsthreebot/0.0.1

### Description:
This is a node template responsible for managing [coredns with 3bot records support](https://coredns.io/) server instance.

### Schema:

- `ztIdentity`: zerotier identity of the coredns container. This is set by the template.
- `backplane` : the network interface name that will answer dns queries only  teh default value (backplane)
- `domain`: authorative domain. If specified, SOA record will be configured for this domain

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

- `install`: creates the coredns container and makes sure it is assigned a zerotier ip but doesn't start the coredns process.
- `start`: start coredns service and create coredns config .
- `stop`: stop the coredns process.
- `uninstall`: stop the coredns process and remove the container.


### Usage example via the 0-robot DSL

```python
robot = j.clients.zrobot.robots['local']
args = {
    'nics': [{'name': 'ten', 'type': 'zerotier', 'ztClient':'zt', 'id': '1d719394044ed153'}]}  
    
coredns = robot.services.create('github.com/threefoldtech/0-templates/corednsthreebot/0.0.1', 'coredns1', data=args)
coredns.schedule_action('install')
coredns.schedule_action('start')
coredns.schedule_action('stop')
coredns.schedule_action('uninstall')
```


### Usage example via the 0-robot CLI

To install coredns `coredns1`:

```yaml
services:
    - github.com/threefoldtech/0-templates/corednsthreebot/0.0.1__coredns1:
          nics:
            - name: 'ten'
            - id: 1d719394044ed153
            - ztClient: 'zt'
            - type: 'zerotier'
          
actions:
    - template: 'github.com/threefoldtech/0-templates/corednsthreebot/0.0.1'
      service: 'corednsthreebot'
      actions: ['install']

```


To start  coredns `coredns1`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/corednsthreebot/0.0.1'
      service: 'coredns1'
      actions: ['start']

```


To stop  coredns `coredns1`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/corednsthreebot/0.0.1'
      service: 'coredns1'
      actions: ['stop']

```