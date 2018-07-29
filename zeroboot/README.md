# Zeroboot setup

## Prerequisite

* Zeroboot environment: The Zeroboot templates are not responsible for setting up the Zeroboot environment, this should be done before starting with the template and make an inventory of the hosts so that it can be used to configure the templates.  

    On how to setup a zeroboot environment, check the [zero-boot howto guide.](https://docs.grid.tf/threefold/info/src/branch/master/howto/zero_boot_hardware.md)  

    Power management using ipmi is supported by the templates. If your hardware supports it, the Racktivity module and setup can be omitted in the [zero-boot howto guide.](https://docs.grid.tf/threefold/info/src/branch/master/howto/zero_boot_hardware.md)

* Inventory environment: The following data from the network will be needed to setup the templates for the environment.
    * Zeroboot (on the router) client needs the following data:
        * hostname/address of the host running it
        * ssh login/username
        * ssh password
        * ZeroTier token
        * ZeroTier network ID
    * For each host/node:
        * hostname
        * ip address
        * mac address
        * zeroboot network
        * When using Racktivity power management:
            * Rackivity module hostname/address
            * Racktivity login/username
            * Racktivity password
            * Racktivity port number the host is connected on
            * Racktivity power module ID when using SE models
        * When using ipmi power management:
            * ipmi interface address for the host
            * ipmi login/username
            * ipmi password

### Preparation for the examples

Start and connect the robot using the templates
```sh
# run a zero robot
zrobot server start -D <zrobot-data-repo> -C <js9-config-repo> -T git@github.com:zero-os/0-boot-templates.git

# connect to the zero robot server
zrobot robot connect zero-boot http://127.0.0.1:6600
```

The examples in this guide uses the ZeroRobot dsl API and Jumpscale which can be executed in a script or the Jumpscale interpreter.

Open Jumpscale
```sh
js9
```

Or import Jumpscale when using as a script
```py
from js9 import j
```

Load the ZeroRobot
```py
# get the robot
robot = j.clients.zrobot.robots['zero-boot']

# check if templates are present
robot.templates.uids
# Out:
# ...
# github.com/zero-os/0-boot-templates/zeroboot_client/0.0.1: ...
# github.com/zero-os/0-boot-templates/zeroboot_racktivity_host/0.0.1: ...
# github.com/zero-os/0-boot-templates/zeroboot_ipmi_host/0.0.1: ...
# ...
```

## Overview templates

For a Zeroboot setup, the following templates are provided in this template repository:

* [zerotier_client](#zerotier_client): Used for the Zeroboot client.
* [ssh_client](#ssh_client): Used for the Zeroboot client.
* [zeroboot_client](#zeroboot_client): Used for managing the zeroboot setup using the Jumpscale zboot client.  
More information about the Jumpscale zboot client can be found [here.](https://github.com/jumpscale/lib9/blob/development/docs/clients/zeroboot_client.md)
* [racktivity_client](#racktivity_client): Used for power management of a host with a racktivity device.
* [ipmi_client](#ipmi_client): Used for power management of a host that supports ipmi.
* [zeroboot_racktivity_host](#zeroboot_racktivity_host): Manages a zeroboot host that has power management using a racktivity device.
* [zeroboot_ipmi_host](#zeroboot_ipmi_host): Manages a zeroboot host that has power management using ipmi.
* [zeroboot_pool](#zeroboot_pool): Manages a pool of zeroboot hosts, used for keeping track of available resources for the reservation template.
* [zeroboot_reservation](#zeroboot_reservation): Manages the reservation of a zeroboot host.

### zerotier_client

The zerotier client is needed for the zeroboot client so it can manage the zerotier network.

Documentation for the template can be found [here](templates/zerotier_client/README.md)

#### Example service creation

```py
data = {
  'token': '<Your-zerotier-token-here>'
}
zt_service = robot.services.create("github.com/zero-os/0-boot-templates/zerotier_client/0.0.1", "zboot1-zt", data=data)
```

### ssh_client

The ssh client is needed for the zeroboot client so it can login into the management host (usually router) and manage the hosts.

Documentation for the template can be found [here](templates/ssh_client/README.md)

#### Example service creation

```py
data = {
  'host': '10.10.1.1',
  'login': 'root',
  'password': '1234'
}
ssh_service = robot.services.create("github.com/zero-os/0-boot-templates/ssh_client/0.0.1", "zboot1-ssh", data=data)
```

### zeroboot_client

The zeroboot client manages a zeroboot environment.

Documentation for the template can be found [here](templates/zeroboot_client/README.md)

#### Example service creation

```py
data = {
  'networkId': '<The-zerotier-networkID-here>',
  'sshClient' : 'zboot1-ssh', # ssh client instance name
  'zerotierClient': 'zboot1-zt', # zerotier client instance name
}
zboot_service = robot.services.create("github.com/zero-os/0-boot-templates/zeroboot_client/0.0.1", "zboot1-zb", data=data)
```

### racktivity_client

The Racktivity client power manages a single racktivity device (can manage multiple devices).

Documentation for the template can be found [here](templates/racktivity_client/README.md)

#### Example service creation

```py
data = {
  'username': 'admin',
  'password': '1234',
  'host': '10.10.2.100',
}
rackt1_service = robot.services.create("github.com/zero-os/0-boot-templates/racktivity_client/0.0.1", "zboot1-rackt1", data=data)
```

### ipmi_client

The ipmi client power manages a single host through ipmi (manages a single host).

Documentation for the template can be found [here](templates/ipmi_client/README.md)

#### Example service creation

```py
data = {
  "bmc": "10.10.2.21", # ipmi interface address of the host
  "user": "ADMIN",
  "password": "1234",
}
ipmi-h21_service = robot.services.create("github.com/zero-os/0-boot-templates/ipmi_client/0.0.1", "zboot1-ipmi-h21", data=data)
```

### zeroboot_racktivity_host

The Zeroboot racktivity host template manages a zeroboot host that has power management using a Racktivity device.

Documentation for the template can be found [here](templates/zeroboot_racktivity_host/README.md)

#### Example service creation

```py
data = {
  'zerobootClient': 'zboot1-zb', # zeroboot client instance name
  'racktivityClient': 'zboot1-rackt1', # racktivity client instance name
  'mac': 'd6-05-78-f2-06-8f',
  'ip': '10.10.2.11',
  'network': '10.10.2.2/24',
  'hostname': 'host-11',
  'racktivityPort': 6,  # port on the racktivity device the host is connected to.
  'racktivityPowerModule': 'P1', # module on the racktivity device the port is on (only for racktivity SE models)
  'lkrnUrl': '<ipxe_LKRN_file_url>',
}
h11_service = robot.services.create("github.com/zero-os/0-boot-templates/zeroboot_racktivity_host/0.0.1", "zboot1-h11", data=data)
```

### zeroboot_ipmi_host

The Zeroboot ipmi host template manages a zeroboot host that has power management using ipmi.

Documentation for the template can be found [here](templates/zeroboot_ipmi_host/README.md)

#### Example service creation

```py
data = {
  'zerobootClient': 'zboot1-zb', # zeroboot client instance name
  'ipmiClient': 'zboot1-ipmi-h21', # ipmi client instance name
  'network': '10.10.2.2/24',
  'hostname': 'host-21',
  'mac': '48-24-ae-3b-80-cc',
  'ip': '10.10.2.21',
  'lkrnUrl': '<ipxe_LKRN_file_url>',
}
h21_service = robot.services.create("github.com/zero-os/0-boot-templates/zeroboot_ipmi_host/0.0.1", "zboot1-h21", data=data)
```

### zeroboot_pool

The zeroboot pool template keeps track of the zeroboot hosts that are available for reservation.

The hosts added to the pool should already have been successfully installed before they can be added, else an exception will the raised.

Documentation for the template can be found [here](templates/zeroboot_pool/README.md)

#### Example service creation

```py
data = {
  'zerobootHosts': ['zboot1-h11','zboot1-h21'] # list of installed zeroboot host instances ready for reservation.
}
pool_service = robot.services.create("github.com/zero-os/0-boot-templates/zeroboot_pool/0.0.1", "zboot1-pool", data=data)
```

### zeroboot_reservation

The zeroboot reservation template manages a reservation of a single host. It reserves an available host from a zeroboot pool service on installation and acts as a proxy for the zeroboot host.

Documentation for the template can be found [here](templates/zeroboot_reservation/README.md)

#### Example service creation

```py
data = {
  'zerobootPool': 'zboot1-pool',
  'lkrnUrl': '<ipxe_LKRN_file_url>',
}
reservation1_service = robot.services.create("github.com/zero-os/0-boot-templates/zeroboot_reservation/0.0.1", "zboot1-res1", data=data)
```

## Example power management of a single host

The following example will show how to do power management of a single zeroboot host for both a Racktivity and ipmi managed host.

The services created in the template examples will be fetched and used for this example.

### Racktivity

Get the racktivity host service.
For the configuration of the service, check the example in the [zeroboot_racktivity_host chapter](#zeroboot_racktivity_host)

```py
# list services (check if required services are running)
robot.services.names

# Out:
# {'zboot1-zt': robot://main/github.com/zero-os/0-boot-templates/zerotier_client/0.0.1?...,
# 'zboot1-ssh': robot://main/github.com/zero-os/0-boot-templates/ssh_client/0.0.1?..,
# 'zboot1-zb': robot://main/github.com/zero-os/0-boot-templates/zeroboot_client/0.0.1?...,
# 'zboot1-rackt1': robot://main/github.com/zero-os/0-boot-templates/racktivity_client/0.0.1?...,
# 'zboot1-h11': robot://main/github.com/zero-os/0-boot-templates/zeroboot_racktivity_host/0.0.1?...,
# ...}

# get the racktivity host service
h11_service = robot.services.get(name="zboot1-h11", template_uid="github.com/zero-os/0-boot-templates/zeroboot_racktivity_host/0.0.1")

# install the host
h11_service.schedule_action("install").wait(die=True).result

# power status
h11_service.schedule_action("power_status").wait(die=True).result
# Out: True
# Means it's on

# power off
h11_service.schedule_action("power_off").wait(die=True).result
h11_service.schedule_action("power_status").wait(die=True).result
# Out: False

# power on
h11_service.schedule_action("power_on").wait(die=True).result
h11_service.schedule_action("power_status").wait(die=True).result
# Out: True
```

### IPMI

Get the ipmi host service.
For the configuration of the service, check the example in the [zeroboot_ipmi_host chapter](#zeroboot_ipmi_host)

```py
# list services (check if required services are running)
robot.services.names

# Out:
# {'zboot1-zt': robot://main/github.com/zero-os/0-boot-templates/zerotier_client/0.0.1?...,
# 'zboot1-ssh': robot://main/github.com/zero-os/0-boot-templates/ssh_client/0.0.1?..,
# 'zboot1-zb': robot://main/github.com/zero-os/0-boot-templates/zeroboot_client/0.0.1?...,
# 'zboot1-ipmi-h21': robot://main/github.com/zero-os/0-boot-templates/ipmi_client/0.0.1?...,
# 'zboot1-h21': robot://main/github.com/zero-os/0-boot-templates/zeroboot_ipmi_host/0.0.1?...,
# ...}

# get the ipmi host service
h21_service = robot.services.get(name="zboot1-h21", template_uid="github.com/zero-os/0-boot-templates/zeroboot_ipmi_host/0.0.1")

# install the host
h21_service.schedule_action("install").wait(die=True).result

# power status
h21_service.schedule_action("power_status").wait(die=True).result
# Out: True
# Means it's on

# power off
h21_service.schedule_action("power_off").wait(die=True).result
h21_service.schedule_action("power_status").wait(die=True).result
# Out: False

# power cycle
# Turns the host off and back on again.
# If the host was powered off, it will power the host back on.
h21_service.schedule_action("power_cycle").wait(die=True).result
h21_service.schedule_action("power_status").wait(die=True).result
# Out: True
```

## Example reservation

The following example will show how to reserve a host.

The host services created in the template examples will be fetched and used for this example.

### Setup

```py
# list services (check if required services are running)
robot.services.names

# Out:
# {'zboot1-zt': robot://main/github.com/zero-os/0-boot-templates/zerotier_client/0.0.1?...,
# 'zboot1-ssh': robot://main/github.com/zero-os/0-boot-templates/ssh_client/0.0.1?..,
# 'zboot1-zb': robot://main/github.com/zero-os/0-boot-templates/zeroboot_client/0.0.1?...,
# 'zboot1-rackt1': robot://main/github.com/zero-os/0-boot-templates/racktivity_client/0.0.1?...,
# 'zboot1-h11': robot://main/github.com/zero-os/0-boot-templates/zeroboot_racktivity_host/0.0.1?...,
# 'zboot1-ipmi-h21': robot://main/github.com/zero-os/0-boot-templates/racktivity_client/0.0.1?...,
# 'zboot1-h21': robot://main/github.com/zero-os/0-boot-templates/zeroboot_ipmi_host/0.0.1?...,
# ...}

# get and install the host services
h11_service = robot.services.get(name="zboot1-h11", template_uid="github.com/zero-os/0-boot-templates/zeroboot_racktivity_host/0.0.1")
h11_service.schedule_action("install").wait(die=True).result
h21_service = robot.services.get(name="zboot1-h21", template_uid="github.com/zero-os/0-boot-templates/zeroboot_ipmi_host/0.0.1")
h21_service.schedule_action("install").wait(die=True).result

# create the pool
data = {
  'zerobootHosts': ['zboot1-h11','zboot1-h21']
}
pool_service = robot.services.create("github.com/zero-os/0-boot-templates/zeroboot_pool/0.0.1", "zboot1-pool", data=data)
```

### Make a reservation

```py
# create a reservation service
data = {
  'zerobootPool': 'zboot1-pool',
  'lkrnUrl': '<ipxe_LKRN_file_url>',
}
reservation_1 = robot.services.create("github.com/zero-os/0-boot-templates/zeroboot_reservation/0.0.1", "zboot1-res1", data=data)

# install will reserve a host from the pool.
# The host reserved host will be powered on by the install action.
reservation_1.schedule_action("install").wait(die=True).result

# get the hostname of the zboot host reserved
reservation_1.schedule_action("host").wait(die=True).result
# Out: zboot1-h21

# get power status
reservation_1.schedule_action('power_status').wait(die=True).result
# Out: True
```

### Release a reservation

To release a reservation, run the `uninstall` action or delete the reservation service
```py
# uninstall action
reservation_1.schedule_action('uninstall').wait(die=True).result

# delete the service
reservation_1.delete()
```
