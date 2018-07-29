## template: github.com/zero-os/0-boot-templates/racktivity_client/0.0.1

### Description:

This template is responsible for configuring the Racktivity client on Jumpscale. Initializing a service from this templates creates a client with the provided configuration.

If the client with instance name already already exists, that instance will be used

### Schema:

- `username`: Racktivity username
- `password`: Racktivity password
- `host`: Rackivity device hostname/address
- `port`: Target port

### Actions:

- `delete`: Deletes the client from Jumpscale and the service
