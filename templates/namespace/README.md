## template: github.com/threefoldtech/0-templates/namespace/0.0.1

### Description:
This template is responsible for managing a 0-db namespace

### Schema:

- `zerodb`: the zerodb service where the namespace is deployed. This is set by the template.
- `size`: the namespace size
- `diskType`: disk type. Valid DiskType value.
- `mode`: zero-db mode. Valid Mode value.
- `public`: public mode. see https://github.com/rivine/0-db#nsset for detail about public mode
- `password`: the namespace password **optional**
- `nsName`: the namespace name. It will be generated if empty.

DiskType enum: 
- `hdd` 
- `ssd`

Mode enum: 
- `user` 
- `direct`
- `seq`

### Actions
- `install`: creates the namespace.
- `info`: returns info about the namespace. 
- `url`: return the public url of the namespace
- `private_url`: return the private url of the namespace
- `uninstall`: removes the namespace from the zerodb
- `connection_info`: returns the connection info

### Usage example via the 0-robot DSL

```python
robot = j.clients.zrobot.robots['main']

args = {
    'size': 10,
    'password': 'password',
}
namespace = robot.services.create('github.com/threefoldtech/0-templates/namespace/0.0.1', 'namespace_one', data=args)
namespace.schedule_action('install')
namespace.schedule_action('info')
```


### Usage example via the 0-robot CLI

To create namespace `namespace_one`:

```yaml
services:
    - github.com/threefoldtech/0-templates/namespace/0.0.1__namespace_one:
          size: 10
          password: 'password'
          
actions:
    - template: 'github.com/threefoldtech/0-templates/namespace/0.0.1'
      service: 'namespace_one'
      actions: ['install']

```


To get info for namespace `namespace_one`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/namespace/0.0.1'
      service: 'namespace_one'
      actions: ['info']

```
