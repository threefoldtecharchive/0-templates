## template: github.com/zero-os/0-templates/alerta/0.0.1

### Description:

This template is responsible for reporting alerts to the alerta server.

### schema:

- `url`: url of the alerta api server that will be connected to. Example url: `http://{address}/api/`

- `apikey`: configured api key used to connect to the alerta server.

- `envname`: envname used to group the alerts.

### Actions

- `process_healthcheck`: process the healthcheck result and update the alerta server with the relevant information.

The alerta service is used by other services to report to alerta(for example, healthcheck results). Below is an example yaml using the node service:

```yaml
services:
- github.com/zero-os/0-templates/alerta/0.0.1__reporter:
    url: "http://{address}/api/"
    apikey: "{apikey}"
    envname: "{envname}"

- github.com/zero-os/0-templates/node/0.0.1__525400123456:
    redisAddr: 172.17.0.1
    redisPort: 6379
    hostname: "myzeros"
    alerta: ['reporter']

actions:
  - template: github.com/zero-os/0-templates/node/0.0.1
    actions: ['install']
```