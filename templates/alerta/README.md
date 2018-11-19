## template: github.com/threefoldtech/0-templates/alerta/0.0.1

### Description:

This template is responsible for reporting alerts to the alerta server.

### schema:

- `url`: url of the alerta api server that will be connected to. Example url: `http://{address}/api/`

- `apiKey`: configured api key used to connect to the alerta server.

- `envName`: envname used to group the alerts.

### Actions

- `send_alert`: send an alert
- `process_healthcheck`: process the healthcheck result and update the alerta server with the relevant information.

### Usage example via the 0-robot DSL
    ```python
    robot = j.clients.zrobot.robots['main']
    args = {
        url: "http://{address}/api/"
        apiKey: "{apikey}"
        envName: "{envname}"
    }
    alerta = robot.services.create('github.com/threefoldtech/0-templates/alerta/0.0.1__reporter', 'alerta', data=args)
    alerta.schedule_action('process_healthcheck')
    ```

The alerta service is used by other services to report to alerta(for example, healthcheck results). Below is an example yaml using the node service:

```yaml
services:
- github.com/threefoldtech/0-templates/alerta/0.0.1__reporter:
    url: "http://{address}/api/"
    apiKey: "{apikey}"
    envName: "{envname}"
```
