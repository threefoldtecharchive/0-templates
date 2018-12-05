from Jumpscale import j
import copy
import netaddr
from zerorobot.template.base import TemplateBase

NODE_CLIENT = 'local'
GATEWAY_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/gateway/0.0.1'


class PublicGateway(TemplateBase):
    version = '0.0.1'
    template_name = "public_gateway"

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.add_delete_callback(self.uninstall)

    def validate(self):
        services = self.api.services.find(template_uid=GATEWAY_TEMPLATE_UID, name='publicgw')
        if len(services) != 1:
            raise RuntimeError('This service requires there to be exactly one gateway deployed with name `publicgw`')
        for forward in self.data.get('portforwards', []):
            if not forward.get('name'):
                raise ValueError('Name is a required attribute for portforward')
            if not isinstance(forward.get('srcport'), int):
                raise ValueError('srcport should be an int')
            if not isinstance(forward.get('dstport'), int):
                raise ValueError('dstport should be an int')
            for protocol in forward.get('protocols', []):
                if protocol not in ['tcp', 'udp']:
                    raise ValueError('Invalid protocol {}'.format(protocol))
            netaddr.IPAddress(forward.get('dstip'))
        for proxy in self.data.get('httpproxies', []):
            if not proxy.get('name'):
                raise ValueError('Name is a required attribute for http proxy')
            if not proxy.get('host'):
                raise ValueError('Host is a required attribute for http proxy')
            if not proxy.get('destinations'):
                raise ValueError('Destinations is a required attribute for http proxy')

    @property
    def _node_sal(self):
        return j.clients.zos.get(NODE_CLIENT)

    @property
    def _gateway_service(self):
        return self.api.services.get(template_uid=GATEWAY_TEMPLATE_UID, name='publicgw')

    def install(self):
        self.logger.info('Install public gateway {}'.format(self.name))
        gw_service = self._gateway_service
        portforwards = self.data.get('portforwards')
        for portforward in portforwards:
            fwd = copy.deepcopy(portforward)
            fwd['srcnetwork'] = 'public'
            fwd['name'] = self._prefix_name(portforward['name'])
            gw_service.schedule_action('add_portforward', args={'forward': fwd}).wait(die=True)

        proxies = self.data.get('httpproxies')
        for proxy in proxies:
            p = copy.deepcopy(proxy)
            p['name'] = self._prefix_name(proxy['name'])
            gw_service.schedule_action('add_http_proxy', args={'proxy': p}).wait(die=True)

    def get_zt_member(self, identity):
        address = identity.split(':')[0]
        for network in self._gateway_service.info()['networks']:
            if network['type'] == 'zerotier':
                client = j.clients.zerotier.get(network['ztClient'])
                ztnetwork = client.network_get(network['id'])
                return ztnetwork.member_get(address=address).data

    def add_portforward(self, forward):
        self.logger.info('Add portforward {}'.format(forward['name']))
        gw_service = self._gateway_service
        fwd = copy.deepcopy(forward)
        fwd['srcnetwork'] = 'public'
        fwd['name'] = self._prefix_name(forward['name'])
        gw_service.schedule_action('add_portforward', args={'forward': fwd}).wait(die=True)
        self.data['portforwards'].append(forward)

    def _prefix_name(self, name):
        return '{}_{}'.format(self.guid, name)

    def remove_portforward(self, name):
        self.logger.info('Remove portforward {}'.format(name))
        pname = self._prefix_name(name)
        self._gateway_service.schedule_action('remove_portforward', args={'name': pname}).wait(die=True)
        for forward in self.data['portforwards']:
            if forward['name'] == name:
                self.data['portforwards'].remove(forward)
                return

    def add_http_proxy(self, proxy):
        self.logger.info('Add http proxy {}'.format(proxy['name']))
        gwproxy = copy.deepcopy(proxy)
        gwproxy['name'] = self._prefix_name(proxy['name'])
        self._gateway_service.schedule_action('add_http_proxy', args={'proxy': gwproxy}).wait(die=True)
        self.data['httpproxies'].append(proxy)

    def remove_http_proxy(self, name):
        self.logger.info('Remove http proxy {}'.format(name))
        pname = self._prefix_name(name)
        self._gateway_service.schedule_action('remove_http_proxy', args={'name': pname}).wait(die=True)
        for proxy in self.data['httpproxies']:
            if proxy['name'] == name:
                self.data['httpproxies'].remove(proxy)
                return

    def info(self):
        gwinfo = self._gateway_service.schedule_action('info').wait(die=True).result
        publicip = ''
        zerotierId = ''
        for network in gwinfo['networks']:
            if network['name'] == 'public':
                publicip = network['config']['cidr']
                continue
            elif network['type'] == 'zerotier':
                zerotierId = network['id']
        data = {
            'portforwards': self.data['portforwards'],
            'httpproxies': self.data['httpproxies'],
            'publicip': publicip,
            'zerotierId': zerotierId
        }
        return data

    def uninstall(self):
        gw_service = self._gateway_service
        self.logger.info('Uninstall publicservice {}'.format(self.name))
        for portforward in self.data['portforwards']:
            name = self._prefix_name(portforward['name'])
            gw_service.schedule_action('remove_portforward', args={'name': name}).wait(die=True)

        proxies = self.data.get('httpproxies')
        for proxy in proxies:
            name = self._prefix_name(proxy['name'])
            gw_service.schedule_action('remove_http_proxy', args={'name': name}).wait(die=True)



