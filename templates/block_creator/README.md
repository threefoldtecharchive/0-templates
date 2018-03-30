## template: github.com/threefoldtoken/0-templates/block_creator/0.0.1

### Description:
This template is responsible for deploying block creator node.

### Schema:

- `rpcPort`: rpc port for the deamon (default 23112)
- `apiPort`: api port (default 23110)
- `node`: reference to the node running the tfchain container
- `walletSeed`: wallet's primary seed, should be set at start
- `walletPassphrase`: wallet passphrase, if omitted, one will be generated
- `walletAddr`: address of the wallet

### Actions
- `install`: create container with tfchain binaries.
- `start`: starts the container and the tfchain daemon process and init wallet.
- `stop`: stops the tfchain daemon process.
- `wallet_address`: return wallet address
- `consensus_stat`: return some statistics about the consensus