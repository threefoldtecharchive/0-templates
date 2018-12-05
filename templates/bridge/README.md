## template: github.com/threefoldtech/0-templates/bridge/0.0.1

### Description:
This template is responsible for creating a bridge on a zero-os node.

### Schema:
  - `hwaddr`: MAC address of the bridge. If none, a one will be created for you
  - `mode`: Networking mode, options are `none`, `static`, and `dnsmasq`
  - `nat`: If true, SNAT will be enabled on this bridge. (IF and ONLY IF an IP is set on the bridge via the settings, otherwise flag will be ignored) (the cidr `attribute` of either static, or dnsmasq modes)
  - `settings`: depending on the mode, different setting need to be passed:
    - `static` mode:
        - `cidr`: bridge will get assigned the given IP address (ip/net)

    - `dnsmasq` mode:  
      - `cidr` : bridge will get assigned the ip in cidr and each running container that is attached to this IP will get IP from the start/end range. Netmask of the range is the netmask part of the provided cidr.
      - `start`:
      - `end`: 

### Actions
- `install`: creates a bridge on a node.
- `uninstall`: delete a bridge.
- `nic_add`: add a nic to the bridge
- `nic_remove`: remove a nic from the bridge
- `nic_list`: list all nic attached to this bridge


### Examples

Install bridge:
```yaml
github.com/threefoldtech/0-templates/bridge/0.0.1__br0:
  mode: none
  nat: false

actions:
  action: ['install']
```

