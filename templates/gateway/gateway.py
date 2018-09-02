from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError

NODE_CLIENT = 'local'


class Gateway(TemplateBase):
    version = '0.0.1'
    template_name = "gateway"

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.recurring_action('_monitor', 30)
        self.add_delete_callback(self.uninstall)

    def validate(self):
        if not self.data['hostname']:
            raise ValueError('Must supply a valid hostname')

    def _monitor(self):
        try:
            self.state.check('actions', 'start', 'ok')
            if not self._gateway_sal.is_running():
                try:
                    self.install()
                    if self._gateway_sal.is_running():
                        self.state.set('state', 'running', 'ok')
                    else:
                        self.state.delete('state', 'running')
                except:
                    self.state.delete('state', 'running')
                    raise
        except StateCheckError:
            # gateway is not supposed to be running
            pass

    @property
    def _node_sal(self):
        return j.clients.zos.get(NODE_CLIENT)

    @property
    def _gateway_sal(self):
        gw = self._node_sal.primitives.from_dict('gateway', self.data)
        gw.name = self.guid
        return gw

    def install(self):
        self.logger.info('Install gateway {}'.format(self.name))
        gateway_sal = self._gateway_sal
        gateway_sal.deploy()
        self.data['ztIdentity'] = gateway_sal.zt_identity
        self.state.set('actions', 'install', 'ok')
        self.state.set('actions', 'start', 'ok')
        self.state.set('state', 'running', 'ok')

    def add_portforward(self, forward):
        self.logger.info('Add portforward {}'.format(forward['name']))
        self.state.check('actions', 'start', 'ok')

        for network in self.data['networks']:
            if network['name'] == forward['srcnetwork']:
                break
        else:
            raise LookupError('Network with name {} doesn\'t exist'.format(forward['srcnetwork']))

        used_sourceports = set()
        for fw in self.data['portforwards']:
            used_sourceports.add(fw['srcport'])
            name, combination = self._compare_objects(fw, forward, 'srcnetwork', 'srcport')
            if name:
                raise ValueError('A forward with the same name exists')
            if combination:
                if set(fw['protocols']).intersection(set(forward['protocols'])):
                    raise ValueError('Forward conflicts with existing forward')
        if not forward['srcport']:
            for suggested_port in range(2000, 10000):
                if suggested_port not in used_sourceports:
                    forward['srcport'] = suggested_port
                    break
            else:
                raise RuntimeError('Could not find free sourceport to use')
    
        self.data['portforwards'].append(forward)

        try:
            self._gateway_sal.configure_fw()
        except:
            self.logger.error('Failed to add portforward, restoring gateway to previous state')
            self.data['portforwards'].remove(forward)
            self._gateway_sal.configure_fw()
            raise
        return forward

    def remove_portforward(self, name):
        self.logger.info('Remove portforward {}'.format(name))
        self.state.check('actions', 'start', 'ok')

        for fw in self.data['portforwards']:
            if fw['name'] == name:
                self.data['portforwards'].remove(fw)
                break
        else:
            return

        try:
            self._gateway_sal.configure_fw()
        except:
            self.logger.error('Failed to remove portforward, restoring gateway to previous state')
            self.data['portforwards'].append(fw)
            self._gateway_sal.configure_fw()
            raise

    def add_http_proxy(self, proxy):
        self.logger.info('Add http proxy {}'.format(proxy['name']))
        self.state.check('actions', 'start', 'ok')

        for existing_proxy in self.data['httpproxies']:
            name, combination = self._compare_objects(existing_proxy, proxy, 'host')
            if name:
                raise ValueError('A proxy with the same name exists')
            if combination:
                raise ValueError("Proxy with host {} already exists".format(proxy['host']))
        self.data['httpproxies'].append(proxy)

        try:
            self._gateway_sal.configure_http()
        except:
            self.logger.error('Failed to add http proxy, restoring gateway to previous state')
            self.data['httpproxies'].remove(proxy)
            self._gateway_sal.configure_http()
            raise

    def remove_http_proxy(self, name):
        self.logger.info('Remove http proxy {}'.format(name))
        self.state.check('actions', 'start', 'ok')

        for existing_proxy in self.data['httpproxies']:
            if existing_proxy['name'] == name:
                self.data['httpproxies'].remove(existing_proxy)
                break
        else:
            return
        try:
            self._gateway_sal.configure_http()
        except:
            self.logger.error('Failed to remove http proxy, restoring gateway to previous state')
            self.data['httpproxies'].append(existing_proxy)
            self._gateway_sal.configure_http()
            raise

    def add_dhcp_host(self, network_name, host):
        self.logger.info('Add dhcp to network {}'.format(network_name))
        self.state.check('actions', 'start', 'ok')

        for network in self.data['networks']:
            if network['name'] == network_name:
                break
        else:
            raise LookupError('Network with name {} doesn\'t exist'.format(network_name))
        dhcpserver = network.setdefault('dhcpserver', {})
        for existing_host in dhcpserver.get('hosts', []):
            if host.get('macaddress') and existing_host['macaddress'] == host['macaddress']:
                raise ValueError('Host with macaddress {} already exists'.format(host['macaddress']))
            if host.get('ipaddress') and existing_host['ipaddress'] == host['ipaddress']:
                raise ValueError('Host with ipaddress {} already exists'.format(host['ipaddress']))
            if existing_host['hostname'] == host['hostname']:
                raise ValueError('Host with hostname {} already exists'.format(host['hostname']))

        gateway_sal = self._gateway_sal
        host_sal = gateway_sal.networks[network_name].hosts.add(host['hostname'], host.get('ipaddress'), host.get('macaddress'))
        host['ipaddress'] = host_sal.ipaddress
        host['macaddress'] = host_sal.macaddress

        dhcpserver['hosts'].append(host)

        try:
            gateway_sal.configure_dhcp()
            gateway_sal.configure_cloudinit()
        except:
            self.logger.error('Failed to add dhcp host, restoring gateway to previous state')
            dhcpserver['hosts'].remove(host)
            gateway_sal.networks[network_name].hosts.remove(host['hostname'])
            gateway_sal.configure_dhcp()
            gateway_sal.configure_cloudinit()
            raise
    
        return host

    def remove_dhcp_host(self, network_name, host):
        self.logger.info('Add dhcp to network {}'.format(network_name))

        self.state.check('actions', 'start', 'ok')

        for network in self.data['networks']:
            if network['name'] == network_name:
                break
        else:
            raise LookupError('Network with name {} doesn\'t exist'.format(network_name))
        dhcpserver = network['dhcpserver']
        for existing_host in dhcpserver['hosts']:
            if existing_host['macaddress'] == host['macaddress']:
                dhcpserver['hosts'].remove(existing_host)
                break
        else:
            raise LookupError('Host with macaddress {} doesn\'t exist'.format(host['macaddress']))

        try:
            self._gateway_sal.configure_dhcp()
            self._gateway_sal.configure_cloudinit()
        except:
            self.logger.error('Failed to remove dhcp, restoring gateway to previous state')
            dhcpserver['hosts'].append(existing_host)
            self._gateway_sal.configure_dhcp()
            self._gateway_sal.configure_cloudinit()
            raise

    def _compare_objects(self, obj1, obj2, *keys):
        """
        Checks that obj1 and obj2 have different names, and that the combination of values from keys are unique
        :param obj1: first dict to use for comparison
        :param obj2: second dict to use for comparison
        :param keys: keys to use for value comparison
        :return: a tuple of bool, where the first element indicates whether the name matches or not,
        and the second element indicates whether the combination of values matches or not
        """
        name = obj1['name'] == obj2['name']
        for key in keys:
            if obj1[key] != obj2[key]:
                return name, False
        return name, True

    def add_network(self, network):
        self.logger.info('Add network {}'.format(network['name']))
        self.state.check('actions', 'start', 'ok')

        for existing_network in self.data['networks']:
            name, combination = self._compare_objects(existing_network, network, 'type', 'id')
            if name:
                raise ValueError('Network with name {} already exists'.format(name))
            if combination:
                raise ValueError('network with same type/id combination already exists')
        self.data['networks'].append(network)

        try:
            self._gateway_sal.deploy()
        except:
            self.logger.error('Failed to add network, restoring gateway to previous state')
            self.data['networks'].remove(network)
            self._gateway_sal.deploy()
            raise

    def remove_network(self, name):
        self.logger.info('Remove network {}'.format(name))
        self.state.check('actions', 'start', 'ok')

        for network in self.data['networks']:
            if network['name'] == name:
                self.data['networks'].remove(network)
                break
        else:
            return
        try:
            self._gateway_sal.deploy()
        except:
            self.logger.error('Failed to remove network, restoring gateway to previous state')
            self.data['networks'].append(network)
            self._gateway_sal.deploy()
            raise

    def add_route(self, route):
        self.logger.info('Add route {}'.format(route['name']))
        self.state.check('actions', 'start', 'ok')

        for existing_network in self.data['networks']:
            name, combination = self._compare_objects(existing_network, route, 'dev', 'dest')
            if name:
                raise ValueError('route with name {} already exists'.format(name))
            if combination:
                raise ValueError('route with same dev/dest combination already exists')

        self.data['routes'].append(route)

        try:
            self._gateway_sal.deploy()
        except:
            self.logger.error('Failed to add route, restoring gateway to previous state')
            self.data['routes'].remove(route)
            self._gateway_sal.deploy()
            raise

    def remove_route(self, name):
        self.logger.info('Remove route {}'.format(name))
        self.state.check('actions', 'start', 'ok')

        for route in self.data['routes']:
            if route['name'] == name:
                self.data['routes'].remove(route)
                break
        else:
            return
        try:
            self._gateway_sal.deploy()
        except:
            self.logger.error('Failed to remove route, restoring gateway to previous state')
            self.data['routes'].append(route)
            self._gateway_sal.deploy()
            raise

    def info(self):
        data = self._gateway_sal.to_dict(live=True)
        return {
            'name': self.name,
            'portforwards': data['portforwards'],
            'httpproxies': data['httpproxies'],
            'networks': data['networks'],
            'routes': data['routes']
        }

    def uninstall(self):
        self.logger.info('Uninstall gateway {}'.format(self.name))
        self._gateway_sal.stop()
        self.state.delete('actions', 'install')
        self.state.delete('actions', 'start')

    def stop(self):
        self.logger.info('Stop gateway {}'.format(self.name))
        self._gateway_sal.stop()
        self.state.delete('actions', 'start')
        self.state.delete('state', 'running')

    def start(self):
        self.logger.info('Start gateway {}'.format(self.name))
        self.state.check('actions', 'install', 'ok')
        self.install()
