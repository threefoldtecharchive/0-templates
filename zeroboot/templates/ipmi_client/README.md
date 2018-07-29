## template: github.com/zero-os/0-boot-templates/ipmi_client/0.0.1

### Description:

This template is responsible for configuring the ipmi client on Jumpscale. Initializing a service from this templates creates a client with the provided configuration.

If the client with instance name already already exists, that instance will be used.

### Schema:

- `bmc`: bmc hostname/address
- `user`: ipmi login username
- `password`: ipmi password
- `port`: ipmi port

### Actions:

- `delete`: Deletes the client from Jumpscale and the service
