## template: github.com/threefoldtoken/0-templates/block_creator_status_reporter/0.0.1

### Description:
This template is responsible for posting the block creator status to the tff-backend app

### Schema:

- `blockCreator`: reference to the block creator service
- `blockCreatorIdentifier`: id representing the block creator upstream
- `postUrlTemplate`: url template where to post the updates. eg http://127.0.0.1:4567/path/to/handler/{block_creator_identifier}/and/maybe/some/more/path

### Actions
- `start`: starts the reporting every 5 minutes
- `stop`: stops the reporting


### Examples:
#### DSL (api interface):
```python
data = {'blockCreator': 'creator_01', 'blockCreatorIdentifier': '007', 'postUrlTemplate': 'http://127.0.0.1:4567/path/to/handler/{block_creator_identifier}/and/maybe/some/more/path'}
bc = robot.services.create('github.com/threefoldtoken/0-templates/block_creator_status_reporter/0.0.1', 'block_creator_status_reporter', data)
bc.schedule_action('start')
```

#### Blueprint (cli interface):
```yaml
services:
    - github.com/threefoldtoken/0-templates/block_creator_status_reporter/0.0.1__block_creator_status_reporter:
        blockCreator: creator_01
        blockCreatorIdentifier: '007'
        postUrlTemplate: http://127.0.0.1:4567/path/to/handler/{block_creator_identifier}/and/maybe/some/more/path


actions:
    - actions: ['start']
      service: block_creator_status_reporter
```
