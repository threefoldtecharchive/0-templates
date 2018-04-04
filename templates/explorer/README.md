## template: github.com/threefoldtoken/0-templates/explorer/0.0.1

### Description:
This template is responsible for deploying an explorer node.

### Schema:

- `rpcPort`: rpc port for the deamon (default 23112)
- `apiPort`: api port (default 23110)
- `node`: reference to the node running the tfchain container
- `dns`: domain name where to expose the explorer web page

### Actions
- `install`: create container with tfchain binaries.
- `start`: starts the container and the tfchain daemon process and init wallet.
- `stop`: stops the tfchain daemon process.