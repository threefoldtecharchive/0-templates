## template: github.com/threefoldtech/0-templates/minio/0.0.1

### Description:
This template is responsible for managing [minio](https://minio.io/) server instance.

### Schema:

- `zdbs`: list of zerodbs endpoints used as backend for minio ex: ['192.168.122.87:9600']
- `namespace`: namespace name to use on the 0-db
- `nsSecret`: secret to use to have access to the namespace on the 0-db servers
- `login`: minio login. End user need to know this login to have access to minio
- `password`: minio password. End user need to know this login to have access to minio
- `privateKey`: encryption private key
- `metaPrivateKey`: metadata encryption private key
- `blockSize`:  block size of the data on minio. Defaults to 1048576 bytes.
- `tlog`: entry of type Tlog. Used to fill the tlog config of the [Transaction Log](https://github.com/threefoldtech/minio/tree/zerostor/cmd/gateway/zerostor#transaction-log).
- `master`: entry of type Tlog. Used to fill the master config of the [Transaction Log](https://github.com/threefoldtech/minio/tree/zerostor/cmd/gateway/zerostor#transaction-log).
- `nodePort`: public port on the node that is forwarded to the minio inside the container. This field is filled by the template


Tlog:
- `namespace`: namespace name
- `address`: zerdb address

### Actions
- `install`: install the minio server. It will create a container on the node and run minio inside the container
- `start`: starts the container and the minio process. 
- `stop`: stops minio process.
- `uninstall`: stop the minio server and remove the container from the node. Executing this action will make you loose all data stored on minio

### States
This service set these states:
- status:
    - running: if OK, minio is running and ready
- actions:
    - install: if OK, install has been done successfully
    - start: if OK, start action has been called, the service will try to stay running

- data_shards: Contains the health of all data shards used by minio. If OK, shards is healthy, if ERROR, shards needs to be healed
- tlog_shards: contains the health of all tlog shards used by minio. If OK, shards is healthy, if ERROR, shards needs to be healed


### Usage example via the 0-robot DSL

To create instance `erp` then register `node1`

```python
robot = j.clients.zrobot.robots['main']

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
minio = robot.services.create('github.com/threefoldtech/0-templates/minio/0.0.1', 'minio', args)
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
