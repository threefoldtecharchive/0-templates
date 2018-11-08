# Service creator tool

This script is responsible for creating the services required for a 0-boot environment.

It requires a data file that contains all the information about the router, ipmi/racitivity, host ip and kernel url. 
You can find example of such files at 

The script supports 3 format:
- yaml: [data_example.yaml](data_example.json)
- json: [data_example.json](data_example.json) 
- csv: 

If pool flag is provided with pool name, all the hosts in the data file that have had services created will be added to that pool.

There is also a `--clean` flag that removes all 0-boot related services before creating the services defined in the data file.

## Usage

The parameters to the script are:
* --robot {str} (-r) : The name of the robot to connect to. (zrobot robot connect main http://127.0.0.1:6600 -> main). If 'debug' the robot will be a MagicMock()
* --data {str} (-d) : CSV file to read the host data from, according to the format described above
* --pool {str} (-p): flag to indicate that all the hosts in the file will be added to a single pool, the string provided sets the pool service name.

Flags:

* --clean (-c): Start from clean env. Deletes all reservation, pool, racktivity host, racktivity client, zeroboot and ssh services from the robot it has access to. 
These are the following template uids:
    * `github.com/zero-os/0-boot-templates/zeroboot_reservation/0.0.1`
    * `github.com/zero-os/0-boot-templates/zeroboot_pool/0.0.1`
    * `github.com/zero-os/0-boot-templates/zeroboot_racktivity_host/0.0.1`
    * `github.com/zero-os/0-boot-templates/racktivity_client/0.0.1`
    * `github.com/zero-os/0-boot-templates/zeroboot_client/0.0.1`
    * `github.com/zero-os/0-boot-templates/ssh_client/0.0.1`

### example

```sh
sudo python3 service_creator.py --data my_farm.yaml --robot local --pool pool1
```


## CSV data file

If you use CSV format for the data file, here is the description of the format.

How the different services are detected is by the title in the first column.
The row underneath the service title has the names of the configurations for that service.
The rows underneath contain the data for the service, matching the configuration titles column indexes.

The different service configurations are separated/terminated by an empty line or EOF.

All titles are case insensitive.

The current supported service and config titles are:
- `zerotier_client`:
    - token: token to access the zerotier API
 - `ssh_client`: SSH client service data
    - `host`: address of the target ssh device
    - `login`: Username for the device
    - `password`: Password for the device
    - `port`: (optional, defaults to 22) SSH port on the device
- `zeroboot_client`: zboot client service data
    - `name`: Name to give the zboot service
    - `networkId`: Zerotier network
    - `zerotierClient`: SSH service to the zboot host/router
 - `ipmi_client`: IPMI client service data
    - `bmc`: address of the ipmi interface
    - `user`: Username for the ipmi interface
    - `password`: Password for the ipmi interface
 - `ipmi_host_data`: ipmi host service data
    - `zboot_service`: zeroboot service name
    - `ipmi_service`: ipmi service for this host
    - `ip`: local ip address of the host
    - `network`: network the host is in
    - `hostname`: hostname of the host
    - `lkrn_url`: Boot url
 - `racktivity_data`: Racktivity client service data
    - `host_address`: address of the racktivity device
    - `hostname`: hostname of the racktivity device, will be used for service name
    - `user`: Username for the racktivity device
    - `password`: Password for the racktivity device
    - `port`: (optional) Client access port on the racktivity device 
 - `rack_host_data`: racktivity host service data
    - `zboot_service`: zeroboot service name
    - `racktivity_data`: racktivity data (format: <racktivity client/service>;<port>;<powermodule>  powermodule is optional, only for SE models)
    - `redundant_racktivity_data`: (optional, meant for a redundant power supply) Format the same as `racktivity_data`
    - `mac`: mac address of the host
    - `ip`: local ip address of the host
    - `hostname`: hostname of the host
    - `lkrn_url`: Boot url

