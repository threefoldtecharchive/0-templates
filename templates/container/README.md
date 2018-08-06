## template: github.com/threefoldtech/0-templates/container/0.0.1

### Description:
This template is responsible for creating a container on zero-os nodes

### Schema:

- `hostname`: container hostname.
- `flist`: url of the root filesystem flist.
- `initProcesses`: a list of type Processes. These are the processes to be started once the container starts.
- `nics`: a list of type Nics. It specifies the configuration of the attached nics to the container.
- `hostNetworking`: a boolean if set to true will make the node networking available to the container.
- `ports`: a list of node-to-container ports mappings. e.g: 8080:80.
- `storage`: ardb storage.
- `mounts`: a list of type Mount mapping mount points from the node to the container.
- `zerotierNetwork`: The node's zerotier network id.
- `privileged`: a boolean indicating whether this will be a privileged container or not.
- `env`: a list of Env describing environment variables to be created on the container.

Mount:
- `source`: mount source on node
- `target`: mount target on container 

Env:
- `name`: name of the environment variable
- `value`: value of the environment variable

Process:
- `name`: name of the executable.
- `pwd`: directory in which the process needs to be started.
- `args`: list of the process' command line arguments.
- `environment`: list of environment variables for the process e.g ['PATH=/usr/bin/local'].
- `stdin`: data that needs to be passed into the stdin of the started process.
- `id`: pid of the process

Nic:
- `type`: value from enum NicType indicating the nic type. 
- `id`: vxlan or vlan id.
- `config`: a dict of NicConfig.
- `name`: nic's name.
- `token`: zerotier token for Nic of tyoe zerotier.
- `hwaddr`: hardware address.

NicConfig:
- `dhcp`: boolean indicating to use dhcp or not.
- `cidr`: cidr for this nic.
- `gateway`: gateway address
- `dns`: list of dns

NicType enum:
- `default`
- `zerotier`
- `vlan`
- `vxlan`
- `bridge`


### Actions:
- `install`: creates a container on a node, starts it and runs all the processes in initProcesses.
- `start`: start a container and run all the initProcesses.
- `stop`: stops a container.



### Usage example via the 0-robot DSL

To install container `zerodbcontainer` on node `525400123456`:

```python
robot = j.clients.zrobot.robots['local']

container_data = {
    'flist': 'https://hub.gig.tech/maxux/zero-db.flist',
    'mounts': [{'source': '/mnt/zdb/one', 'target': '/zdb'}],
    'nics': [{'type': 'default'}],
}
container = robot.services.create('github.com/threefoldtech/0-templates/container/0.0.1', 'zerodbcontainer', data=container_data)
container.schedule_action('install')

container.schedule_action('start')
container.schedule_action('stop')
```

### Usage example via the 0-robot CLI

To install container `zerodbcontainer` on node `525400123456`:

```yaml
services:
    - github.com/threefoldtech/0-templates/container/0.0.1__zerodbcontainer:
          flist: 'https://hub.gig.tech/maxux/zero-db.flist'
          storage: 'ardb://hub.gig.tech:16379'
          nics:
            - type: 'default'
          mounts:
            - source: '/mnt/zdb/one'
              target: '/zdb'
actions:
    - template: 'github.com/threefoldtech/0-templates/container/0.0.1'
      service: 'zerodbcontainer'
      actions: ['install']

```


To start container `zerodbcontainer`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/container/0.0.1'
      service: 'zerodbcontainer'
      actions: ['start']

```


To stop container `zerodbcontainer`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/container/0.0.1'
      service: 'zerodbcontainer'
      actions: ['stop']

```