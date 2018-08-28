## template: github.com/threefoldtech/0-templates/gateway/0.0.1

### Description:
This template is responsible for creating a gateway on zero-os nodes
It configures caddy, dnsmasq, nftables and cloud-init to work together to provide gateway services

### Schema:

- `hostname`: container hostname.
- `domain`: Domain for the private networks
- `networks`: a list of type Networks. It specifies the configuration of the attached networks to the container.
- `routes`: contains the routing table of the gateway
- `portforwards`: list of Portforward tcp/udp forwards from public network to private network
- `httpproxies`: liost of HTTPProxy. Reverse http/https proxy to allow one public ip to host multiple http services
- `certificates`: List of Certificate
- `ztIdentity`: zerottier identity of the gateway container

PortForward:
- `protocols`: IPProtocol enum
- `srcport`: Port to forward from
- `srcnetwork`: Network name to get the src ip from
- `dstip`: IPAddress to forward to
- `dstport`: Port to forward to
- `name`: portforward name

IPProtocol enum:
- `tcp`
- `udp`

Network:
- `type`: value from enum NetworkType indicating the network type. 
- `id`: vxlan or vlan id.
- `config`: a dict of NetworkConfig.
- `name`: network's name.
- `ztClient`: reference to zerotier client to authorize this node into the zerotier network
- `hwaddr`: hardware address.
- `dhcpserver`: Config for dhcp entries to be services for this network.
- `public`: Boolean flag that defines if the network should be treated as public or not.

NetworkConfig:
- `dhcp`: boolean indicating to use dhcp or not.
- `cidr`: cidr for this network.
- `gateway`: gateway address
- `dns`: list of dns

NetworkType enum:
- `default`
- `zerotier`
- `vlan`
- `vxlan`
- `bridge`

DHCPServer:
- `nameservers`: IPAddresses of upstream dns servers
- `hosts`: Host entries to provided leases for

Host:
- `hostname`: Hostname to pass to lease info
- `macaddress`: MACAddress used to identify lease info
- `ipaddress`: IPAddress service for this host
- `ip6address`: IP6Address service for this host
- `cloudinit`: Cloud-init data for this host

CloudInit:
- `userdata`: Userdata as string (yaml string)
- `metadata`: Metadata as string (yaml string)

HTTPProxy:
- `host`: http proxy host
- `destinations`: list of destinations
- `types`: list of HTTPType enum
- `name`: http proxy name

HTTPType enum:
- `http`
- `https`

Route:
- `name`: logical name of the route
- `device`: device name
- `destination`: destination network
- `gateway`: gateway, optional

### Actions:
- `install`: creates a gatewa on a node, starts it and configures all services
- `start`: start a gateway
- `stop`: stops a gateway
- `add_portforward`: Adds a portforward to the firewall
- `remove_portforward`: Removes a portforward from the firewall
- `add_http_porxy`: Adds a httpproxy to the http server
- `remove_http_porxy`: Removes a httpproxy from the http server
- `add_dhcp_host`: Adds a host to a dhcp server
- `remove_dhcp_host`: Remove a host from a dhcp server
- `add_network`: Adds a network to the gateway
- `remove_network`: Remove a network from the gateway
- `add_route`: add a route to the gateway
- `remove_route`: remove a route from the gateway
- `info`: Retreive information about your gateway

### Examples:

#### DSL (api interface)
```python
api = j.clients.zrobot.robots['main']
print('Create GW')
vmmac = '54:40:12:34:56:78'
vmip = '192.168.103.2'
data = {
        'hostname': 'mygw',
        'domain': 'lan',
        'networks': [{
            'name': 'public',
            'type': 'vlan',
            'id': 0,
            'config': {
                'cidr': '192.168.59.200/25',
                'gateway': '192.168.59.254'
            }
        }, {
            'name': 'private',
            'type': 'vxlan',
            'id': 100,
            'config': {
                'cidr': '192.168.103.1/24',
            },
            'dhcpserver': {
                'nameservers': ['1.1.1.1'],
                'hosts': [{
                    'hostname': 'myvm',
                    'macaddress': vmmac,
                    'ipaddress': vmip
                    }]
            }
        }],
        'portforwards': [{
            'srcport': 34022,
            'srcnetwork': 'public',
            'dstip': vmip,
            'dstport': 22,
            'name': 'sshtovm'
        }],
        'httpproxies': [{
            'host': '192.168.59.200',
            'destinations': ['http://{}:8000'.format(vmip)],
            'types': ['http'],
            'name': 'httpproxy'
        }]

}
gwservice = api.services.find_or_create(GW_UID, service_name='mygw', data=data)
gwservice.schedule_action('install').wait(die=True)
```
