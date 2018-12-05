## template: github.com/threefoldtech/0-templates/hardware_check/0.0.1

### Description:
This template is responsible for checking if the hardware specs of a node matches the expected specs and sending a message to a telegram chat with the result of the check.

### Schema:
- `supported`: a list of HWCombo.
- `botToken`: token of the telegram bot to be use to send the telegram message.
- `chatId`: id of the telegram groupchat to send the message to.

HWCombo:
- `hddCount`: expected number of hdds.
- `ssdCount`: expected number of ssds.
- `ram`: expected amount of ram (in mibi bytes - MiB).
- `cpu`: model name of expected cpu.
- `name`: name of this hardware combination.

### Actions:
- `check`: checks the hardware specs of a specific node and the message accordingly.

    Arguments:
    - `node_name`: the name of the node service.


### Usage example via the 0-robot DSL

To check if node `node1` has supported hardware specs

```python
robot = j.clients.zrobot.robots['local']

args = {
    'supported':[{
        'hddCount': 2,
        'ssdCount': 2,
        'ram': 7150,
        'cpu': 'intel',
        'name': 'name',
    }],
    'botToken': 'thisisabottoken',
    'chatId': '1823737123',
}
hw_check= robot.services.create('github.com/threefoldtech/0-templates/hardware_check/0.0.1', 'hw_check', args)
hw_check.schedule_action('check', args={'node_name':'node1'})
```

### Usage example via the 0-robot CLI

To check if node `node1` has supported hardware specs


```yaml
services:
    - github.com/threefoldtech/0-templates/hardware_check/0.0.1__hc:
        supported:
          - hddCount: 2
            ssdCount: 2
            ram: 7150,
            cpu: 'intel'
            name: 'name'
        botToken: 'thisisabottoken'
        chatId': '1823737123'

actions:
    - template: github.com/threefoldtech/0-templates/hardware_check/0.0.1
      service: 'hc'
      actions: ['check']
      args:
        node_name: 'node1'
```

