## template: github.com/zero-os/0-boot-templates/zeroboot_ipmi_client/0.0.1

### Description:

This template is responsible for managing a zeroboot host with ipmi power management.
Through this template, one can manage the power state and boot configuration of the host.

### Schema:

- zerobootClient: zeroboot Jumpscale client instance name
- ipmiClient: ipmi Jumpscale client instance name
- network: Zeroboot network that contains the host
- mac: Target mac address
- ip: Target IP address
- hostname: Target hostname
- lkrnUrl: URL to LKRN file, if provided, it will be set on install

### Actions:

- install: installs the service
- uninstall: uninstalls the service
- host: returns the hostname of the node
- ip: returns the ip of the node
- power_on: ipmi powers on the host
- power_off: ipmi powers off the host
- power_cycle: ipmi powers cycles the host (turns off for a few seconds and turns it back on)
- power_status: Returns the power status of the host (`True` if on, `False` if off)
- monitor: Checks if the power status matches the one of the internally saved state. On install the internal state will be fetched using `power_status`, then will be updated by the actions `power_on` and `power_off`.  
If the last action before calling `monitor` was `power_on` but the current state of the host is `False`(off), it will turn the  power to the host back on.
- configure_ipxe_boot: Set the ipxe boot configuration with provided LKRN URL (calling `power_cycle` is needed to use the new boot configuration).
