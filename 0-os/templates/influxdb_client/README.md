## template: influxdb_Client

### Description:
This template is responsible for create influxdb client 

### Schema:

- `host`:  the host name e.g 'localhost'
- `port`: port of the influxdb client, by default 8086
- `login`: username by default root
- `passwd`: password by default root
- `ssl`: Use HTTPS for requests by default false
- `verifySsl`: Verify that HTTPS is working by connecting to InfluxDB  by default false

### Actions

- `install`: create influxdb client 
- `delete`: delete influxdb client


### Examples:
#### DSL (api interface):
```python
data = {'host' :'localhost', 'passwd':'root', 'port':'8086', 'ssl': False ,'login': 'root' ,'verifySsl': False}
stat = robot.services.create('github.com/zero-os/0-templates/influxdb_client/0.0.1','eecffbc-2041-4722-9c51-1700c9d5cf88', data)
stat.schedule_action('install')
```

#### Blueprint (cli interface):
```yaml
services:
    - github.com/zero-os/0-templates/influxdb_client/0.0.1__eecffbc-2041-4722-9c51-1700c9d5cf88:
        host : 'localhost'
        port : '8086'
        login : 'root'
        passwd : 'root'
        ssl : False
        verifySsl : False

actions:
    - template: github.com/zero-os/0-templates/influxdb_client/0.0.1
      service: 'eecffbc-2041-4722-9c51-1700c9d5cf88'
      actions: ['install']
```
