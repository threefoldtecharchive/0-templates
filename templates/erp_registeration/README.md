## template: github.com/threefoldtech/0-templates/erp_registeration/0.0.1

### Description:
This template is responsible for registering a node in odoo if it wasn't already registered.

### Schema:
- `url`: url of the odoo server.
- `db`: name of the database.
- `username`: username to use to connect to odoo.
- `password`: password to use to connect to odoo.
- `botToken`: token of the telegram bot to be use to send the telegram message.
- `chatId`: id of the telegram groupchat to send the message to.


### Actions:
- `register`: register a node in model `stock.production.lot`.
    
    Arguments:
    - `node_name`: the name of the node service 

### Usage example via the 0-robot DSL

To create instance `erp` then register `node1`

```python
robot = j.clients.zrobot.robots['local']

args = {
    'url': 'odoo_url',
    'db': 'test',
    'username': 'user',
    'password': 'password',
    'botToken': 'XomAJANa',
    'chatId': '1823737123',
}
erp = robot.services.create('github.com/threefoldtech/0-templates/erp_registeration/0.0.1', 'erp', args)
erp.schedule_action('register', args={'node_id':'node1'})
```

### Usage example via the 0-robot CLI

To create instance `erp` then register `node1`

```yaml
services:
    - github.com/threefoldtech/0-templates/erp_registeration/0.0.1__erp:
          url: 'odoo_url'
          db: 'test'
          username: 'user'
          password: 'password'
          botToken: 'XomAJANa'
          chatId: '1823737123'
actions:
    - template: 'github.com/threefoldtech/0-templates/erp_registeration/0.0.1'
      service: 'erp'
      actions: ['register']
      args:
        node_id: 'node1'

```
