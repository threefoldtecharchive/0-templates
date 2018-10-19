## template: github.com/threefoldtech/0-templates/s3_redundant/0.0.1

### Description:
This template is responsible for managing a redundant s3 which consists of an active and passive s3 instances

### Schema:

- `mgmtNic`: Nic info for the minio vm.
- `farmerIyoOrg`: farmer organization to use for capacity.
- `dataShards`: 0-stor data shards config. Defaults to 16.
- `parityShards`: 0-stor parity shards config. It must be equal to or less than the dataShard. Defaults to 4.
- `storageType`: s3 storage type. Must be a value of StorageType. Defaults to `hdd`.
- `storageSize`: total s3 storage size in GB.
- `minioLogin`: minio web login.
- `minioPassword`: minio web password, minimum 8 characters.
- `minioBlockSize`: block size of the data on minio. Defaults to 1048576 bytes.
- `nsPassword`: the namespace password. If not supplied, a random one will be generated **optional**

Nic:
- `id`: zerotier network id or vxlan id.
- `ztClient`: zerotier client name to be used for authorization in case of a zerotier nic.

Enum StorageType:
- `hdd`
- `ssd`

### Actions:
- `install`: creates and installs two s3 instances. One acitve and one passive.
- `uninstall`: uninstalls both s3 instances.
- `urls`: returns the active and passive s3 urls.
- `start_active`: start the active s3 instance.
- `stop_active`: stop the active s3 instance.
- `upgrade_active`: upgrade the active s3 instance.
- `start_passive`: start the passive s3 instance.
- `stop_passive`: stop the passive s3 instance.
- `upgrade_passive`: upgrade the passive s3 instance.


### Examples:
#### DSL (api interface):
```python
data = {
    'farmerIyoOrg': 'sarah',
    'mgmtNic': {'id':'9f77fc393e820576', 'ztClient': 'main'},
    'storageType': 'hdd',
    'storageSize': 50000,
    'minioLogin': 'login',
    'minioPassword': 'password',
}
s3_redundant = api.services.create('github.com/threefoldtech/0-templates/s3_redundant/0.0.1','one', data)
s3_redundant.schedule_action('install')
```

#### Blueprint (cli interface):
```yaml
services:
    - github.com/threefoldtech/0-templates/s3_redundant/0.0.1__one:
        mgmtNic:
          id: 9f77fc393e820576
          ztClient: zt
        farmerIyoOrg: sarah
        storageType: hdd
        storageSize: 50000
        minioLogin: login
        minioPassword: password

actions:
    - template: github.com/threefoldtech/0-templates/s3_redundant/0.0.1
      service: 'one'
      actions: ['install']

```
