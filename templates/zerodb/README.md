## template: github.com/threefoldtech/0-templates/zerodb/0.0.1

### Description:
This template is responsible for managing 0-db.

### Schema:

- `mode`: a value from enum Mode representing the 0-db mode. Defaults to `user`.
- `sync`: boolean indicating whether all write should be sync'd or not. Defaults to `false`.
- `path`: path to use for storing zdb data. Needs to be a btrfs path.
- `admin`: admin password. Set by the template if not supplied.
- `namespaces`: list of Namespace to be deployed on this zerodb. **optional**
- `nics`: list of nics to create for the zerodb container. **optional**
- `ztIdentity`: zerotier identity of the zerodb container. This is set by the template.
- `nodePort`: public listening port, set by the template

Nic:
- `id`: vxlan or vlan id
- `type`: NicType enum specifying the nic type
- `hwaddr`: nic's macaddress
- `name`: nic name
- `ztClient`: zerotier client instance name to use to authorize.

NicType enum: 
- `default` 
- `vlan`
- `vxlan`
- `bridge`

Mode enum:
- `user`: the default user key-value mode.
- `seq`: sequential keys generated.
- `direct`: direct position by key.

Namespace:
- `name`: name of the namespace.
- `size`: maximum size of the namespace in GB.
- `password`: admin password for the namespace.
- `public`: boolean indicating whether namespace is public or not.


### Actions
- `install`: create and start a container with 0-db.
- `start`: starts the container and the 0-db process. 
- `stop`: stops the 0-db process.
- `namespace_create`: create a new namespace. Only admin can do this.
- `namespace_info`: returns basic information about a namespace
- `namespace_list`: returns an array of all available namespaces.
- `namespace_set`: change a namespace setting/property. Only admin can do this.
- `namespace_url`: return the public url of the namespace
- `namespace_private_url`: return the private url of the namespace



### Usage example via the 0-robot DSL

```python
robot = j.clients.zrobot.robots['local']
args = {
    'sync': True,
    'mode': 'user',
    'admin': 'password'
}
zdb = robot.services.create('github.com/threefoldtech/0-templates/zerodb/0.0.1', 'zerodb1', data=args)
zdb.schedule_action('install')

zdb.schedule_action('start')

zdb.schedule_action('namespace_list')
zdb.schedule_action('namespace_info', args={'name':'namespace'})
zdb.schedule_action('namespace_create', args={'name':'namespace'})
zdb.schedule_action('namespace_set', args={'name':'namespace', 'value': 9, 'prop': 'size'})

zdb.schedule_action('stop')
```


### Usage example via the 0-robot CLI

To install zerodb `zerodb1`:

```yaml
services:
    - github.com/threefoldtech/0-templates/zerodb/0.0.1__zerodb1:
          sync: True
          mode: 'user'
          admin: 'password'
          path: '/mnt/data/'
          
actions:
    - template: 'github.com/threefoldtech/0-templates/zerodb/0.0.1'
      service: 'zerodb1'
      actions: ['install']

```


To start  zerodb `zerodb1`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/zerodb/0.0.1'
      service: 'zerodb1'
      actions: ['start']

```


To stop  zerodb `zerodb1`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/zerodb/0.0.1'
      service: 'zerodb1'
      actions: ['stop']

```


