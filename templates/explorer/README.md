## template: github.com/threefoldtoken/0-templates/explorer/0.0.1

### Description:
This template is responsible for deploying an explorer node.

### Schema:

- `rpcPort`: rpc port for the daemon (default 23112)
- `apiPort`: api port (default 23110)
- `node`: reference to the node running the tfchain container
- `domain`: domain name where to expose the explorer web page
- `network`: network to join, default standard
- `tfchainFlist`: the flist to be used for the tfchain (default: https://hub.gig.tech/tfchain/ubuntu-16.04-tfchain-latest.flist)
- `explorerFlist`: the flist to be used for the explorer (default: https://hub.gig.tech/tfchain/caddy-explorer-latest.flist)

### Actions
- `install`: create container with tfchain binaries.
- `start`: starts the container and the tfchain daemon process and init wallet.
- `stop`: stops the tfchain daemon process.
- `consensus_stat`: return some statistics about the consensus
- `gateway_stat`: return some statistics about the gateway

### Examples:
#### DSL (api interface):
```python
data = {'node':'node1', 'domain': 'explorer.tft.com'}
explorer = robot.services.create('github.com/threefoldtoken/0-templates/explorer/0.0.1','explorer', data)
explorer.schedule_action('install')
explorer.schedule_action('start')
```

#### Blueprint (cli interface):
```yaml
services:
    - github.com/threefoldtoken/0-templates/explorer/0.0.1__explorer:
        node: node1
        domain: explorer.tft.com

actions:
    - actions: ['install','start']
      service: explorer
```