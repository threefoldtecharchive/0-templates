## template: github.com/zero-os/0-templates/zerotier_client/0.0.1

### Description:
This template is responsible for configuring the zerotier client on jumpscale. Initializing a service from this templates creates a client with the correct configuration.

### Schema:

- `token`: the token for the zerotier api.


### Actions:
- `add_to_robot`: Add zerotier_client on a node robot
  - `url`: Url of the node robot
  - `serviceguid`: Serviceguid to create the zerotier_client for
- `remove_from_robot`: delete the client from jumpscale.
  - `url`: Url of the node robot
  - `serviceguid`: Serviceguid the zerotier_client was created for
- `delete`: delete the client from jumpscale.
- `delete`: delete the client from jumpscale.


### Usage example via the 0-robot DSL

To create zerotier_client `client` and execute action `delete`:

```python
robot = j.clients.zrobot.robots['local']

args = {
    'token': 'Ximdhaua',
}
zt = robot.services.create('github.com/zero-os/0-templates/zerotier_client/0.0.1', 'client', args)
zt.schedule_action('delete')
```

### Usage example via the 0-robot CLI

To create zerotier_client `client`:

```yaml
services:
    - github.com/zero-os/0-templates/zerotier_client/0.0.1__client:
          token: 'Ximdhaua'
```

to delete zerotier_client `client`:

```yaml
actions:
    - template: 'github.com/zero-os/0-templates/zerotier_client/0.0.1'
      service: 'client'
      actions: ['delete']
```
