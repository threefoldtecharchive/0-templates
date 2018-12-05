from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from testconfig import config
import random

class GWManager:
    def __init__(self, parent, service_name=None):
        self.gw_template = 'github.com/threefoldtech/0-templates/gateway/0.0.1'
        self._parent = parent
        self.logger = self._parent.logger
        self.robot = self._parent.remote_robot
        self._gw_service = None
        if service_name:
            self._gw_service = self.robot.service.get(name=service_name)  

    @property
    def service(self):
        if self._gw_service == None:
            self.logger.error('- GW_service is None, Install it first.')
        else:
            return self._gw_service

    def install(self, wait=True, **kwargs):
        self.default_data = {
            'hostname': self._parent.random_string(),
            'networks': [{'name': 'public_nic', 'type': 'default', 'public': True, 'id': ''}],
            'portforwards': [],
            'httpproxies': [],
            'domain': '',
            'certificates': [],
            'routes': [],
            'ztIdentity': '',
        }
        if kwargs:
            self.default_data.update(kwargs)
            
        self.gw_service_name = self._parent.random_string()
        self.logger.info('Install {} gateway'.format(self.gw_service_name))
        self._gw_service = self.robot.services.create(self.gw_template, self.gw_service_name, self.default_data)
        self._gw_service.schedule_action('install').wait(die=wait)

    def add_portforward(self, data):
        return self.service.schedule_action('add_portforward', args=data).wait(die=True)
    
    def remove_portforward(self, name):
        return self.service.schedule_action('remove_portforward', args={'name': name}).wait(die=True)

    def add_http_proxy(self, proxy):
        return self.service.schedule_action('add_http_proxy', {'proxy': proxy}).wait(die=True)

    def remove_http_proxy(self, name):
        return self.service.schedule_action('remove_http_proxy', args={'name': name}).wait(die=True)

    def add_dhcp_host(self, network_name, host):
        return self.service.schedule_action('add_dhcp_host', args={'network_name': network_name, 'host': host}).wait(die=True)

    def remove_dhcp_host(self, network_name, host):
        return self.service.schedule_action('remove_dhcp_host', args={'network_name': network_name, 'host': host}).wait(die=True)

    def add_network(self, network):
        return self.service.schedule_action('add_network', args={'network': network}).wait(die=True)

    def remove_network(self, name):
        return self.service.schedule_action('remove_network', args={'name': name}).wait(die=True)

    def add_route(self, route):
        return self.service.schedule_action('add_route', args={'route': route}).wait(die=True)

    def remove_route(self, name):
        return self.service.schedule_action('remove_route', args={'name': name}).wait(die=True)

    def info(self):
        return self.service.schedule_action('info').wait(die=True)
    
    def start(self):
        return self.service.schedule_action('start').wait(die=True)

    def stop(self):
        return self.service.schedule_action('stop').wait(die=True)
    
    def uninstall(self):
        return self.service.schedule_action('uninstall').wait(die=True)