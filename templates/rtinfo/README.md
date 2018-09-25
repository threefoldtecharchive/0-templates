## template: github.com/threefoldtech/0-templates/node_capacity/0.0.1

### Description
This template runs an rtinfo client on the local zos host.

### Schema

- `address`: IP address or dns name of the rtinfod server that aggregates the rtinfo.
- `port`: Port where the rtinfod server is listening for client connections (default: `9930`)
- `disks`: List of prefixes of disk names to watch (e.g. `["sd"]` to watch `sda`, `sdb`, `sdc`, ... disks)  
    (default: `[""]` which pushes all watchable disks to rtinfod)
