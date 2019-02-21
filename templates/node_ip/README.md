## template: github.com/threefoldtech/0-templates/node_ip/0.0.1

### Description:
This template add an ip address on one of the interface of the node.

### Schema:

- `cidr`: ip adress and netmask e.g: `192.168.1.1/32`
- `interface`: the name of the interface which to set the address
- `gateway`: If specified, the default gateway of the machine will be replace by the value of this field
             the equivalent of `ip r del default, ip r add default via {gateway}` will be executed


### Actions
- install: add the address to the interface
- uninstall: remove the address from the interface