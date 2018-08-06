## template: github.com/threefoldtech/0-templates/public_gateway/0.0.1

### Description:
This template makes it possible to easily share a gateway

### Schema:

- `portforwards`: list of Portforward tcp/udp forwards from public network to private network
- `httpproxies`: liost of HTTPProxy. Reverse http/https proxy to allow one public ip to host multiple http services

PortForward:
- `protocols`: IPProtocol enum
- `srcport`: Port to forward from
- `dstip`: IPAddress to forward to
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

### Actions:
- `install`: creates a the initial forwards
- `get_zt_member`: Get information about a member inside the zerotier network of the public gateway
- `add_portforward`: Adds a portforward to the firewall
- `remove_portforward`: Removes a portforward from the firewall
- `add_http_porxy`: Adds a httpproxy to the http server
- `remove_http_porxy`: Removes a httpproxy from the http server

### Examples:

#### DSL (api interface)
```python
api = j.clients.zrobot.robots['main']
print('Create Public Service')
data = {
        'portforwards': [{
            'srcport': 34022,
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
service = api.services.find_or_create(PS_UID, service_name='myservices', data=data)
service.schedule_action('install').wait(die=True)
```
