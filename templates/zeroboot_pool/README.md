## template: github.com/zero-os/0-boot-templates/zeroboot_pool/0.0.1

### Description:

This template is responsible for keeping track of a pool of zeroboot hosts (zeroboot_ipmi_host or zeroboot_racktivity_host).

### Schema:

- zerobootHosts: A list of zeroboot instance names

### Actions:

- add: Add a zeroboot host to the pool

    Argmuments:
    - host: name of the host service to add to the pool
- remove: Remove a zeroboot host from the pool

    Argmuments:
    - host: name of the host service to remove to the pool
- unreserved_host: Returns a zeroboot host instance that has not been reserved yet.  
It does this by checking which hosts in the pool do not have an installed reservation service (template: `github.com/zero-os/0-boot-templates/zeroboot_reservation`)

    Arguments:
    - caller_guid: will skip service with this guid to prevent deadlock.
- pool_hosts: Returns all the host instances of the pool
- power_on: Powers on all the hosts in the pool
- power_off: Powers off all the hosts in the pool
- power_cycle: Power cycles all the hosts in the pool
