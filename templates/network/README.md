## template: github.com/threefoldtech/0-templates/network/0.0.1

### Description:
This template is responsible for managing a network on zero-os node.

The node service also tries to configure all the network service that it finds on a node.
So networks are automatically reconfigure after a reboot.

### Schema:

- `cidr`: CIDR to be used for backend network
- `vlan`: VlanTag to be used for vxlan traffic
- `bonded`: should the backend be bonded over 2 interfaces? optional, default to False
- `driver`: will ensure kernel module is loaded and interfaces are up. optional


### Actions
- `configure`: configure the network on the node
- `uninstall`: remove the configuration for the network


### Examples

Install node:
```yaml
github.com/threefoldtech/0-templates/network/0.0.1__storage:
  cidr: 192.168.0.1/24
  vlan: 110
  bonded: True
  driver: ''

actions:
  action: ['configure']
```