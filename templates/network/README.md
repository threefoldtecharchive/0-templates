## template: github.com/threefoldtech/0-templates/network/0.0.1

### Description:
This template is responsible for managing a network on zero-os node.

The node service also tries to configure all the network service that it finds on a node.
So networks are automatically reconfigure after a reboot.


- `cidr`: CIDR to be used for backend network
- `vlan`: VlanTag to be used for vxlan traffic
- `bonded`: should the backend be bonded over 2 interfaces? optional, default to False
- `driver`: will ensure kernel module is loaded and interfaces are up. optional
- `testIp`: if set, the monitor task will check that this ip is reachable from the node, if not a self healing action is taking
- `mtu`: optional mtu, default to 9000
- `usedInterfaces`: interfaces that have been configure, this is filled by the template

> Note: make sure that testIp is always UP and reachable otherwise an un-necessary link restart will keep happening every 30 second

### Actions
- `configure`: configure the network on the node
- `uninstall`: remove the configuration for the network


### Examples

Install node:
```yaml
github.com/threefoldtech/0-templates/network/0.0.1__storage:
  cidr: 192.168.0.2/24
  vlan: 110
  bonded: True
  driver: ''
  testIp: 192.168.0.1

actions:
  action: ['configure']
```
