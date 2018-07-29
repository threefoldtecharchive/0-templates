# Service creator tool

This script is responsible for creating zeroboot host services. If a host service already exists with a certain hostname from the data (CSV) file, adding the host will be skipped.

This script can also create the racktivity client services if not already present on the robot.

If pool flag is provided with pool name, all the hosts in the data file that have had services created will be added to that pool.

There is also a `--clean` flag that removes all zboot related services before creating the services defined in the data file.

## CSV source file

All the configurations of the services can be inserted into one CSV file.

How the different services are detected is by the title in the first column.
The row underneath the service title has the names of the configurations for that service.
The rows underneath contain the data for the service, matching the configuration titles column indexes.

The different service configurations are separated/terminated by an empty line or EOF.

All titles are case insensitive.

The current supported service and config titles are:
 - `ssh_data`: SSH client service data
    - `host_address`: address of the target ssh device
    - `hostname`: hostname of the device, will be used for service name
    - `user`: Username for the device
    - `password`: Password for the device
    - `port`: (optional, defaults to 22) SSH port on the device
- `zboot_data`: zboot client service data
    - `name`: Name to give the zboot service
    - `ztier_network`: Zerotier network
    - `ssh_service`: SSH service to the zboot host/router
    - `ztier_service`: (optional) zerotier service/client name
 - `ipmi_data`: IPMI client service data
    - `host_address`: address of the ipmi interface
    - `hostname`: hostname of the ipmi device, will be used for service name
    - `user`: Username for the ipmi interface
    - `password`: Password for the ipmi interface
    - `port`: (optional) Client access port on the ipmi device 
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
    - `network`: network the host is in
    - `hostname`: hostname of the host
    - `lkrn_url`: Boot url

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
sudo python3 service_creator.py --data ~/Downloads/be-scale-2.csv --robot local --pool pool1
```
