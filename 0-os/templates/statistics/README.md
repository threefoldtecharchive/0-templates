## template: Statistics gathering 

### Description:
This template is responsible for get statistics of node then add it in InfluxDB to Visualization in grafana
### Schema:

- `instanceName`: instance name that created from influxdb_Client template .

### Actions
- `install`: get the reporting every 5 minutes
- `uninstall`: stops the reporting


### Examples:
#### DSL (api interface):
```python
data = {'instanceName': 'influxdb_client_created'}
stat = robot.services.create('github.com/zero-os/0-templates/statistics/0.0.1','1e2b8c6b-b5b9-42c1-99f4-f9149dc25743')
stat.schedule_action('install')
```

#### Blueprint (cli interface):
```yaml
services:
    - github.com/zero-os/0-templates/statistics/0.0.1__1e2b8c6b-b5b9-42c1-99f4-f9149dc25743:
        instanceName : 'influxdb_client_created'

actions:
    - template: github.com/zero-os/0-templates/statistics/0.0.1
      service: '1e2b8c6b-b5b9-42c1-99f4-f9149dc25743'
      actions: ['install']
```
