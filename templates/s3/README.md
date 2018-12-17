## template:  github.com/threefoldtech/0-templates/s3/0.0.1

### Description:
This template is responsible for managing s3 instance. It supports creating both an active and a passive s3 instance.

### Schema:

- `mgmtNic`: Nic info for the minio vm.
- `farmerIyoOrg`: farmer organization to use for capacity.
- `dataShards`: 0-stor data shards config. Defaults to 16.
- `parityShards`: 0-stor parity shards config. Default to 4.
- `storageType`: s3 storage type. Must be a value of `StorageType`. Defaults to hdd.
- `storageSize`: total s3 storage size in GB.
- `namespaces`: list of `Namespace` used for this instance, this is set by the template and used to keep track of the namespaces and their health.
- `tlog`: entry of type `Namespace`, holding info about the tlog namespace. This is set by the template.
- `master`: entry of type `Namespace`. If supplied by the user, then this s3 is a passive s3. The namespace should be the tlog of another s3 which will be the master of this instance.
- `minioLogin`: minio web login.
- `minioPassword`: minio web password, minimum 8 characters.
- `minioUrls`: the minio web urls, this is set by the template.
- `minioBlockSize`: block size of the data on minio. Defaults to 1048576 bytes.
- `nsName`: the namespace name.
- `nsPassowrd`: the namespace password. If not supplied, a random one will be generated. **optional**
- `excludeNodesVM` list of node to avoid using when deploying VM and Vdisk

Nic:
- `id`: zerotier network id or vxlan id.
- `ztClient`: zerotier client name to be used for authorization in case of a zerotier nic.

Enum StorageType:
- `hdd`
- `ssd`

Namespace:
- `name`: namespace service name 
- `node`: node id of the node the namespace is deplopyed on
- `url`: node zrobot address

Urls:
- `public`: URL of minio over the public network
- `storage`: URL of minio over the storage network

### Actions:
- `install`: creates s3 instance by creating all the required namespace, then creating a zoos vm with a minio running on it and connects minio to those namespaces.
- `uninstall`: deletes all the namespacs and zeroos vm on which minio runs.
- `url`: returns the minio web urls
- `start`: start the minio instance
- `stop`: stop the minio instance
- `upgrade`: upgrade the minio flist
- `tlog`: return the tlog info
- `namespace_nodes`: returns node id of all the nodes used for namespace creation for this s3 instance

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
    'nsName': 'namespace',

}
s3 = api.services.create(' github.com/threefoldtech/0-templates/s3/0.0.1','three', data)
s3.schedule_action('install')
```

#### Blueprint (cli interface):
```yaml
services:
    -  github.com/threefoldtech/0-templates/s3/0.0.1__three:
        mgmtNic:
          id: 9f77fc393e820576
          ztClient: zt
        farmerIyoOrg: sarah
        storageType: hdd
        storageSize: 50000
        minioLogin: login
        minioPassword: password
        nsName: namespace

actions:
    - template:  github.com/threefoldtech/0-templates/s3/0.0.1
      service: 'three'
      actions: ['install']

```
