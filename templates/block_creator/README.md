# template: github.com/threefoldtoken/0-templates/block_creator/0.0.1

### Description:
This template is responsible for deploying block creator node.

### Schema:

- `rpcPort`: rpc port for the deamon (default 23112)
- `apiPort`: api port (default 23110)
- `node`: reference to the node running the tfchain container
- `walletSeed`: wallet's primary seed, should be set at start
- `walletPassphrase`: wallet passphrase, if omitted, one will be generated
- `walletAddr`: address of the wallet
- `network`: network to join, default standard
- `tfchainFlist`: the flist to be used for the tfchain (default: https://hub.gig.tech/tfchain/ubuntu-16.04-tfchain-latest.flist)
- `parentInterface`: parent interface for macvlan, if not set then discovered automatically

### Actions
- `install`: create container with tfchain binaries.
- `start`: starts the container and the tfchain daemon process and init wallet.
- `stop`: stops the tfchain daemon process.
- `wallet_address`: return wallet address
- `wallet_amount`: return the amount of token in the wallet
- `consensus_stat`: return some statistics about the consensus
- `start_peer_discovery`: create and install service for scanning network for new peers.
- `delete_peer_discovery`: delete peer discovery service.

### Examples:

#### DSL (api interface):

```python
data = {'node':'node1'}
bc = robot.services.create('github.com/threefoldtoken/0-templates/block_creator/0.0.1','block_creator', data)
bc.schedule_action('install')
bc.schedule_action('start')
bc.schedule_action('start_peer_discovery')
```

#### Blueprint (cli interface):

```yaml
services:
    - github.com/threefoldtoken/0-templates/block_creator/0.0.1__block_creator:
        node: node1

actions:
    - actions: ['install','start']
      service: block_creator
```
