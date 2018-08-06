## template: github.com/threefoldtech/0-templates/vdisk/0.0.1

### Description:
This template is responsible for managing a vdisk

### Schema:

- `size`: the vdisk size
- `diskType`: the type of the disk to use for the namespace
- `mountPoint`: mount point of the disk
- `filesystem`: filesystem to create on the disk
- `zerodb`: the zerodb the namespace is created on
- `nsName`: the name of the namespace created on zerodb
- `label`: label to be given to the disk when it is attached to a vm

### Actions
- `install`: creates the vdisk and namespace.
- `info`: returns info about the namespace. 
- `url`: return the public url of the namespace.
- `private_url`: return the private url of the namespace.
- `uninstall`: uninstall the vdisk by deleting the namespace

### Usage example via the 0-robot DSL

```python
robot = j.clients.zrobot.robots['main']

args = {
    'size': 10,
    'diskType': 'hdd',
    'label': 'label',
}
vdisk = robot.services.create('github.com/threefoldtech/0-templates/vdisk/0.0.1', 'vdisk_one', data=args)
vdisk.schedule_action('install')
vdisk.schedule_action('info')
```


### Usage example via the 0-robot CLI

To create vdisk `vdisk_one`:

```yaml
services:
    - github.com/threefoldtech/0-templates/vdisk/0.0.1__vdisk_one:
          size: 10
          diskType: 'hdd'
          label: 'label'
          
actions:
    - template: 'github.com/threefoldtech/0-templates/vdisk/0.0.1'
      service: 'vdisk_one'
      actions: ['install']

```


To get info for vdisk `vdisk_one`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/vdisk/0.0.1'
      service: 'vdisk_one'
      actions: ['info']

```
