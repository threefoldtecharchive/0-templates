## template: github.com/jumpscale/digital_me/s3/0.0.1

### Description:
This template is responsible for managing s3 instance

### Schema:

- `mgmtNic`: Nic info for the minio vm.
- `farmerIyoOrg`: farmer organization to use for capacity
- `dataShards`: 0-stor data shards config
- `parityShards`: 0-stor parity shards config
- `storageType`: s3 storage type. Must be a value of StorageType
- `storageSize`: s3 storage size
- `namespaces`: list of Namespace, this is set by the template
- `minioLogin`: minio web login
- `minioPassword`: minio web password, minimum 8 characters
- `minioUrl`: the minio web url, this is set by the template.

The attributes are only relevant in case of a vxlan nic:
- `gateway`: the name of the gateway service to use for networking
- `gatewayRobot`: the name of the gateway robot the gateway service lives on
- `gatewayNetwork`: the name of the gateway network to be used to generate the vm ip and macaddress. 
- `vmIp`: the ip assigned to the vm by the gateway. This is set by the template.


Nic:
- `id`: zerotier network id or vxlan id.
- `ztClient`: zerotier client name to be used for authorization in case of a zerotier nic.
- `type`: NicType

NicType:
- `vxlan`
- `zerotier`

Enum StorageType:
- `hdd`
- `ssd`

Namespace:
- `name`: namespace service name 
- `node`: node id of the node the namespace is deplopyed on
- `url`: node zrobot address


### Actions:
- `install`: creates s3 instance by creating all the required namespaces and connects minio to those namespaces.
- `uninstall`: deletes all the namespacs and zeroos vm on which minio runs.
- `url`: returns the minio web url
- `start`: start the minio instance
- `stop`: stop the minio instance
- `upgrade`: upgrade the minio flist

### Examples:
#### DSL (api interface):
```python
data = {
    'farmerIyoOrg': 'sarah',
    'mgmtNic': {'id':'9f77fc393e820576', 'ztClient': 'main'},
    'storageType': 'hdd',
    'storageSize': 10,
    'minioLogin': 'login',
    'minioPassword': 'password',
}
s3 = api.services.create('github.com/jumpscale/digital_me/s3/0.0.1','three', data)
s3.schedule_action('install')
```

#### Blueprint (cli interface):
```yaml
services:
    - github.com/jumpscale/digital_me/s3/0.0.1__three:
        mgmtNic:
          id: 9f77fc393e820576
          ztClient: zt
        farmerIyoOrg: sarah
        storageType: hdd
        storageSize: 10
        minioLogin: login
        minioPassword: password

actions:
    - template: github.com/jumpscale/digital_me/s3/0.0.1
      service: 'three'
      actions: ['install']

```
