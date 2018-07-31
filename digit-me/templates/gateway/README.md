## template: github.com/jumpscale/digital_me/gateway/0.0.1

### Description:

This Gateway template provides a bridge between your own personal `private` gateway and a (public gateway)[https://github.com/zero-os/0-templates/tree/master/templates/public_gateway]
It abstracts all the logic required to create public forwards and http(s) proxies.

### Schema:

- `hostname`: Container hostname.
- `domain`: Domain for the private networks
- `nodeId`: Node ID that will be looked up at capacity.threefoldtoken.com to connect to deploy private gateway
- `publicGatewayRobot`: Instance of the node robot to connect to deploy public gateway service (will be picked automatically)
- `portforwards`: list of Portforward tcp/udp forwards from public network to private network
- `httpproxies`: list of HTTPProxy. Reverse http/https proxy to allow one public ip to host multiple http services
- `networks`: Private networks to connect to, (public will be automatically connected to a public gateway)

Network:
- `type`: value from enum NetworkType indicating the network type. 
- `id`: vxlan or vlan id.
- `config`: a dict of NetworkConfig.
- `name`: network's name.
- `ztClient`: reference to zerotier client to authorize this node into the zerotier network
- `dhcpserver`: Config for dhcp entries to be services for this network.

NetworkConfig:
- `cidr`: cidr for this network.
- `gateway`: gateway address

NetworkType enum:
- `default`
- `zerotier`
- `vlan`
- `vxlan`
- `bridge`
- `passthrough`

DHCP:
- `nameservers`: IPAddresses of upstream dns servers
- `hosts`: Host entries to provided leases for
- `poolStart`
- `poolSize`

Host:
- `hostname`: Hostname to pass to lease info
- `macaddress`: MACAddress used to identify lease info
- `ipaddress`: IPAddress service for this host
- `ip6address`: IP6Address service for this host
- `cloudinit`: Cloud-init data for this host

CloudInit:
- `userdata`: Userdata as string (yaml string)
- `metadata`: Metadata as string (yaml string)

PortForward:
- `protocols`: IPProtocol enum
- `srcport`: Port to forward from
- `vm`: Name of a digital me vm to connect to
- `dstport`: Port to forward to
- `name`: portforward name

IPProtocol enum:
- `tcp`
- `udp`

HTTPProxy:
- `host`: http proxy host
- `destinations`: list of destinations
- `types`: list of HTTPType enum
- `name`: http proxy name

HTTPType enum:
- `http`
- `https`

HTTPDestination:
- `vm`: Name of a digital me vm to connect to
- `port`: Port on digital me vm to connect to


### Actions:
- `install`: creates a gateway on nodeRobot, starts it and configures all services
- `add_portforward`: Adds a portforward to the firewall
- `remove_portforward`: Removes a portforward from the firewall
- `add_http_porxy`: Adds a httpproxy to the http server
- `remove_http_porxy`: Removes a httpproxy from the http server
- `add_network`: Adds a network to the gateway
- `remove_network`: Remove a network from the gateway
- `info`: Retrieve information about your gateway
- `uninstall`: stop the gateway and clean up everything. **This action will delete your data.**


### Examples:

#### DSL (api interface)

```python
# create dm gw
DM_GW_UID = 'github.com/jumpscale/digital_me/gateway/0.0.1'
MPYPRIVATE = 'e4da7455b2c4c429'

api = j.clients.zrobot.robots['main']
data = {
    'hostname': 'mygw',
    'domain': 'lan',
    'nodeId': '544546f60261',
    'networks': [{
        'name': 'private',
        'type': 'zerotier',
        'public': False,
        'id': MPYPRIVATE,
        'ztClient': 'work'
    }],
}

dmgw = api.services.find_or_create(DM_GW_UID, service_name='dm_gw', data=data)
# install
dmgw.schedule_action('install').wait(die=True)

# add proxy that will proxy traffic from my.domain.com to the port 8080 of the vm 'my_vm'
proxy = {'name': 'myproxy', 'host': 'my.domain.com', 'types': ['http'], 'destinations': [{'vm': 'my_vm', 'port': 8080}]}
dmgw.schedule_action('add_http_proxy', args={'proxy': proxy}).wait(die=True)

# add a port forward that will forward the port 9022 of the public IP of the gateway to the port 22 of the vm 'my_vm'
forward = {'protocols':['tcp'],'srcport': 9022,'dstport':22,'vm':'my_vm','name':'my_vm_ssh'}
dmgw.schedule_action('add_portforward',args={'forward':forward})

# remove proxy
dmgw.schedule_action('remove_http_proxy', args={'name': 'myproxy'}).wait(die=True) 

# remove port forward
dmgw.schedule_action('remove_portforward', args={'name': 'my_vm_ssh'}).wait(die=True) 
```