## template: github.com/threefoldtech/0-templates/node/0.0.1

### Description:
This template is responsible for managing a zero-os node.

### Schema:

- `hostname`: the name of the host. It will be automatically filled when the node is created by the `zero_os_bootstrap` service. **optional**
- `version`: the version of the zero-os. It set by the template.
- `uptime`: node uptime in seconds


### Actions
- `install`: installs a node and makes it manageable by zero-robot.
- `reboot`: stops all containers and vms and reboots the node.
- `info`: returns node os info.
- `stats`: returns the node aggregated statistics.
- `processes`: returns the list of processes running on the node.
- `os_version`: returns the node version
- `create_zdb_namespace`: create zdb namespace to be used by vdisk or namespace

#### Create ZDB Namespace

This action will create a ZDB namespace on the node, based on the arguments supplied if needed it will prepare a disk of the correct type and deploy a ZDB server on it alternatively it will create a namespace on an existing ZDB

Parameters:
- `disktype`: Disktype used by ZDB, SSD or HDD
- `mode`: Mode to run ZDB in seq, user or direct
- `password`: Namespace password
- `public`: Indicates if the namespace is public or not
- `size`: Size of the namespace in GiB

This action will return the name of the ZDB service used and the name of the namespace that was created


### Examples

Install node:
```yaml
github.com/threefoldtech/0-templates/node/0.0.1__525400123456:
  hostname: "myzeros"

actions:
  action: ['install']
```

Reboot Node:
```yaml
actions:
  template: github.com/threefoldtech/0-templates/node/0.0.1
  name: 525400123456
  actions: ['reboot']
```

Create Namespace:
```yaml
actions:
  template: github.com/threefoldtech/0-templates/node/0.0.1
  name: 525400123456
  actions: ['create_zdb_namespace']
  args:
    disktype: HDD
    mode: seq
    password: mypassword
    public: false
    size: 10

```

