## template: github.com/zero-os/0-boot-templates/zerotier_client/0.0.1

### Description:
This template is responsible for configuring the zerotier client on jumpscale. Initializing a service from this templates creates a client with the correct configuration.

### Schema:

- `token`: the token for the zerotier api.


### Actions:
- `delete`: delete the client from jumpscale.


### Usage example via the 0-robot DSL

To create zerotier_client `client` and execute action `delete`:

```python
from zerorobot.dsl import ZeroRobotAPI
api = ZeroRobotAPI.ZeroRobotAPI()
robot = api.robots['main']

args = {
    'token': 'Ximdhaua',
}
zt = robot.api.services.create('github.com/zero-os/0-boot-templates/zerotier_client/0.0.1', 'client', args)
zt.schedule_action('delete')
```

### Usage example via the 0-robot CLI

To create zerotier_client `client`:

```yaml
services:
    - github.com/zero-os/0-boot-templates/zerotier_client/0.0.1__client:
          token: 'Ximdhaua'
```

to delete zerotier_client `client`:

```yaml
actions:
    - template: 'github.com/zero-os/0-boot-templates/zerotier_client/0.0.1'
      service: 'client'
      actions: ['delete']
```
