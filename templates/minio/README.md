## template: github.com/threefoldtech/0-templates/minio/0.0.1

### Description:
This template is responsible for managing [minio](https://minio.io/) server instance.

### Schema:

- `zdbs`: list of zerodbs endpoints used as backend for minio ex: ['192.168.122.87:9600']
- `namespace`: namespace name to use on the 0-db
- `nsSecret`: secret to use to have access to the namespace on the 0-db servers
- `login`: minio login. End user need to know this login to have access to minio
- `password`: minio password. End user need to know this login to have access to minio
- `container`: reference to the container on which minio will be running. This is set by the template
- `listenPort`: the port minio will bind to
- `privateKey`: encryption private key
- `metaPrivateKey`: metadata encryption private key

### Actions
- `install`: install the minio server. It will create a container on the node and run minio inside the container
- `start`: starts the container and the minio process. 
- `stop`: stops minio process.
- `uninstall`: stop the minio server and remove the container from the node. Executing this action will make you loose all data stored on minio


### Usage example via the 0-robot DSL

To create instance `erp` then register `node1`

```python
from zerorobot.dsl import ZeroRobotAPI
api = ZeroRobotAPI.ZeroRobotAPI()
robot = api.robots['main']

args = {
    'zerodbs': [
    '192.168.122.87:9900',
    '192.168.122.87:9901',
    '192.168.122.87:9902',
    ],
    'login': 'admin',
    'password': 'password',
    'namespace': 'namespace',
    'privateKey': 'ab345678901234567890123456789012s',
}
minio = api.services.create('github.com/threefoldtech/0-templates/minio/0.0.1', 'minio', args)
minio.schedule_action('install')
minio.schedule_action('start')
minio.schedule_action('stop')
minio.schedule_action('uninstall')

```

### Usage example via the 0-robot CLI

To install instance `minio` on node `547c5d299411`

```yaml
services:
    - github.com/threefoldtech/0-templates/minio/0.0.1__minio:
          zerodbs:
            - 192.168.122.87:9900
            - 192.168.122.87:9901
            - 192.168.122.87:9902
          login: admin
          password: password
          namespace: namespace
          privateKey: ab345678901234567890123456789012

actions:
    - template: github.com/threefoldtech/0-templates/minio/0.0.1
      service: 'minio'
      actions: ['install']
```

To start instance `minio`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/minio/0.0.1'
      service: 'minio'
      actions: ['start']
```

To stop instance `minio`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/minio/0.0.1'
      service: 'minio'
      actions: ['stop']
```

To uninstall instance `minio`:

```yaml
actions:
    - template: 'github.com/threefoldtech/0-templates/minio/0.0.1'
      service: 'minio'
      actions: ['uninstall']
```