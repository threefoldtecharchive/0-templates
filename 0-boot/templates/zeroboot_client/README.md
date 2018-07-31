## template: github.com/zero-os/0-boot-templates/zeroboot_client/0.0.1

### Description:

This template is responsible for configuring the zeroboot client on Jumpscale. Initializing a service from this templates creates a client with the provided configuration.

If the client with instance name already already exists, that instance will be used.

### Schema:

- `networkId`: Zerotier network ID
- `sshClient`: SSH jumpscale client instance name
- `zerotierClient`: Zerotier jumpscale client instance name

### Actions:

- `delete`: Deletes the client from Jumpscale and the service
