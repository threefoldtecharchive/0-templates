## template: github.com/threefoldtech/0-templates/zeroos_client/0.0.1

### Description:
This template is responsible for configuring a zeroos client on jumpscale.

### Schema:

- `host`: the redis address the client uses to connect to zeroos
- `port`: the redis port the client uses to connect to zeroos
- `password`: password used by redis to connect to zeroos
- `ssl`: boolean indicating if ssl is enabled or not
- `db`: redis database number. Defaults to 0
- `timeout`: redis socket timeout
- `unixSocket`: unix socket path

### Actions:
- `delete`: delete the client from Jumpscale.

