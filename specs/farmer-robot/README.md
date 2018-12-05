# Farming robot specifications

First, let's situate the farming robot in the grid. Check the architecture diagram: https://github.com/threefoldfoundation/info_grid/blob/master/docs/tf_technology/zero_robot/robots.md

## Definitions

- **Farm**: A farm is a group of one or multiple 0-OS node geographically close and own by the same farmer.
- **Farmer**: Owner of a farm. He's the one who provide capacity to the grid by connecting hardward running 0-OS to the grid.

## Farming robot responsability

- Know the location and how to access of the node of the farm
- Manage capacity reservation for the farm
  - The farming robot is the robot that is going to create the primitives service on the node robots after a reservation has been done
- Manage and monitor the nodes of the farm
  - the farming robot can turn on/off nodes according to the demand of capacity so the farm stays as green as possible
  - this is mostly the zero-boot templates: https://github.com/zero-os/0-boot-templates
- Managed the public IPs of the farm
  - it is the farming robot that know what public IP the farm can use, and do the capacity planning of this pool of public IPs
- somehow the farming robot will have to update the http://capacity.threefoldtoken.com/ to reflect the used capacity of a farm so user can know what is still available to reserve

## SAL
Here is a scaffold of the interfaces and objects needed in the SAL

### Exceptions
- `OutOfIps` Exception is raised for Pool not having any free IP or for PoolsManager when the underlying pools don't have any free IPs.

### Objects:
```
IPPool:
  id, str
  network, str
  subnetmask, str
  gateway, str
  name, str
  ips, list(str)
```
Note: IPs is a list of a selected IPs in the network, in practice you never have a full hosts range, and it needs to be carefully set to avoid multiple pools having the same IP available.


### Interfaces

`IPPoolsManager` manages a list of pools and keeps track of reservations done through it.

```
IPPoolsManager:
  get_free_ip(pool_id=None) -> (pool_id, ip) : reserves an IP from a certain pool
  get_any_free_ip() -> (pool_id, ip) : reserves an IP from any of the managed pools
  release_ip(pool_id, ip) return an ip to the pool
  is_reserved(ipaddr) -> checks if ipaddr is reserved ip
  is_free_ip(ipaddr) -> checks if ipaddr is free 
  available_ips -> collected available ips from the underlying pools
  reserved_ips -> collects reserved ips from the underlying pools
```

## Templates

- IP_lease: Service that represent a public IP
  - actions:
    - info: return information about the IP lease: ip, lease timeout,...
    - uninstall: put the IP back to the pool it belongs

- Public_IP_Pool: 
  - actions:
    - reserve: reserve an IP from the pool. This action will create an instance of the IP_lease
    - info: return info about the pool: how much public ip available,...
  - schema:
      - id, str
      - network, str
      - subnetmask, str
      - gateway, str
      - name, str
      - ips, list(str)



- reservation_manager:   Service responsible to do the capacity planning of the reservation. It will choose on which node to deploy the services reserved.
  - actions:
    - reserve_vm(cpu, memory): create a VM service on one of the node
    - reserver_gateway(): create a GW service on on of the node
    - reserve_zdb_namespace(size, type): create a zdb namespace on of the node node
    - info: return information regarding the capacity (how much used/free,...)

