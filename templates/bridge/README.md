## template: github.com/threefoldtech/0-templates/bridge/0.0.1

### Description:
This template is responsible for creating a bridge on a zero-os node.

### Schema:
  - `HWAddr`: MAC address of the bridge. If none, a one will be created for you
  - `Mode`: Networking mode, options are `none`, `static`, and `dnsmasq`
  - `Nat`: If true, SNAT will be enabled on this bridge. (IF and ONLY IF an IP is set on the bridge via the settings, otherwise flag will be ignored) (the cidr `attribute` of either static, or dnsmasq modes)
  - `Settings`: depending on the mode, different setting need to be passed:
    - `static` mode:
        - `CIDR`: bridge will get assigned the given IP address (ip/net)

    - `dnsmasq` mode:  
      - `CIDR` : bridge will get assigned the ip in cidr and each running container that is attached to this IP will get IP from the start/end range. Netmask of the range is the netmask part of the provided cidr.
      - `Start`:
      - `End`: 

### Actions
- `install`: installs a node and makes it manageable by zero-robot.
- `uninstall`: stops all containers and vms and reboots the node.
- `nic_add`: add a nic to the bridge
- `nic_remove`: remove a nic from the bridge
- `nic_list`: list all nic attached to this bridge


### Examples

Install node:
```yaml
github.com/threefoldtech/0-templates/bridge/0.0.1__br0:
  Mode: none
  Nat: false

actions:
  action: ['install']
```