import copy
import random
from urllib.parse import urlparse

from requests import HTTPError

from js9 import j
from zerorobot.template.base import TemplateBase

PUBLIC_GW_ROBOTS = ["http://gw1.robot.threefoldtoken.com:6600", "http://gw2.robot.threefoldtoken.com:6600", "http://gw3.robot.threefoldtoken.com:6600"]

GW_UID = 'github.com/zero-os/0-templates/gateway/0.0.1'
PGW_UID = 'github.com/zero-os/0-templates/public_gateway/0.0.1'
ZEROTIERCLIENT_UID = 'github/zero-os/0-templates/zerotier_client/0.0.1'
DM_VM_UID = 'github.com/jumpscale/digital_me/vm/0.0.1'


BASEPORT = 10000


class Gateway(TemplateBase):
    version = '0.0.1'
    template_name = 'gateway'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.add_delete_callback(self.uninstall)
        self._robot_url = None

    def validate(self):
        if not self.data['nodeId']:
            raise ValueError('Invalid input, Vm requires nodeId')

        capacity = j.clients.grid_capacity.get(interactive=False)
        try:
            node, _ = capacity.api.GetCapacity(self.data['nodeId'])
        except HTTPError as err:
            if err.response.status_code == 404:
                raise ValueError('Node {} does not exist'.format(self.data['nodeId']))
            raise err

        self._robot_url = node.robot_address
        j.clients.zrobot.get(self.data['nodeId'], data={'url': self._robot_url})
        self._robot_api = j.clients.zrobot.robots[self.data['nodeId']]

    @property
    def _public_robot_api(self):
        if not self.data.get('publicGatewayRobot'):
            self.data['publicGatewayRobot'] = random.choice(PUBLIC_GW_ROBOTS)
        roboturl = self.data['publicGatewayRobot']
        robotname = urlparse(roboturl).netloc
        j.clients.zrobot.get(robotname, {'url': roboturl}, interactive=False)
        return j.clients.zrobot.robots[robotname]

    def _get_gw_service(self):
        return self._robot_api.services.get(template_uid=GW_UID, name=self.guid)

    def _get_pgw_service(self):
        return self._public_robot_api.services.get(template_uid=PGW_UID, name=self.guid)

    def install(self):
        gwdata = {
            'hostname': self.data['hostname'],
            'networks': copy.deepcopy(self.data['networks']),
            'domain': self.data['domain'],
        }
        for network in gwdata['networks']:
            if network['type'] == 'zerotier' and network.get('ztClient'):
                zerotierservice = self.api.services.get(name=network['ztClient'])
                data = {'url': self._robot_url, 'serviceguid': self.guid}
                zerotierservice.schedule_action('add_to_robot', args=data).wait(die=True)
                # set the name of the zerotier client to the name of the client created on the node robot
                network['ztClient'] = self.guid
            network['public'] = False

        pgwservice = self._public_robot_api.services.find_or_create(PGW_UID, self.guid, {})
        pgwservice.schedule_action('install').wait(die=True)
        pginfo = pgwservice.schedule_action('info').wait(die=True).result
        gwdata['networks'].append({
            'name': 'publicgw',
            'type': 'zerotier',
            'id': pginfo['zerotierId'],
            'public': True
        })

        gwservice = self._robot_api.services.find_or_create(GW_UID, self.guid, gwdata)
        gwservice.schedule_action('install').wait(die=True)
        self._update_portforwards(gwservice, pgwservice)
        self._update_proxies(gwservice, pgwservice)

    def _lookup_by_name(self, collection, name, data=None):
        data = data or self.data
        for item in data[collection]:
            if item['name'] == name:
                return item

    def _get_info(self, gwservice, pgwservice):
        gwservice = gwservice or self._get_gw_service()
        pgwservice = pgwservice or self._get_pgw_service()
        gwinfo = gwservice.schedule_action('info').wait(die=True).result

        for network in gwinfo['networks']:
            if network['public']:
                ztip = network['config']['cidr'].split('/')[0]
                break
        else:
            raise LookupError('Could not find ZT IP on gateway')
        return {'gwservice': gwservice, 'pgwservice': pgwservice,
                'ztip': ztip, 'gwinfo': gwinfo}

    def _update_portforwards(self, gwservice=None, pgwservice=None):
        info = self._get_info(gwservice, pgwservice)
        gwservice = info['gwservice']
        pgwservice = info['pgwservice']
        ztip = info['ztip']
        gwinfo = info['gwinfo']
        tobeconfigured = self.data['portforwards'][:]

        # remove forwards we don't want anymore
        usedports = set()
        for actualforward in gwinfo['portforwards']:
            type_, _, fwdname = actualforward['name'].partition('_')
            if type_ != 'forward':
                continue
            configuredforward = self._lookup_by_name('portforwards', fwdname)
            if not configuredforward:
                gwservice.schedule_action('remove_portforward', args={'name': actualforward['name']}).wait(die=True)
                pgwservice.schedule_action('remove_portforward', args={'name': fwdname}).wait(die=True)
            else:
                usedports.add(actualforward['srcport'])
                tobeconfigured.remove(configuredforward)
        # add forwards
        vmips = {}
        for forward in tobeconfigured:
            vmname = forward['vm']
            if vmname not in vmips:
                vmips[vmname] = self._get_vm_ip(vmname)
            port = BASEPORT
            while port in usedports:
                port += 1
            usedports.add(port)
            pgwforward = {
                'name': forward['name'],
                'srcport': forward['srcport'],
                'dstport': port,
                'dstip': ztip,
                'protocols': forward['protocols'],
            }
            pgwservice.schedule_action('add_portforward', args={'forward': pgwforward}).wait(die=True)
            gwforward = {
                'name': 'forward_{}'.format(forward['name']),
                'srcnetwork': 'publicgw',
                'srcport': port,
                'dstport': forward['dstport'],
                'dstip': vmips[vmname],
                'protocols': forward['protocols'],
            }
            try:
                gwservice.schedule_action('add_portforward', args={'forward': gwforward}).wait(die=True)
            except:
                pgwservice.schedule_action('remove_portforward', args={'name': pgwforward['name']}).wait(die=True)
                raise

    def _update_proxies(self, gwservice=None, pgwservice=None):
        info = self._get_info(gwservice, pgwservice)
        gwservice = info['gwservice']
        pgwservice = info['pgwservice']
        ztip = info['ztip']
        pgwinfo = pgwservice.schedule_action('info').wait(die=True).result

        tobeconfigured = self.data['httpproxies'][:]

        # remove proxies
        toremoveforwards = []
        for actualproxy in pgwinfo['httpproxies']:
            name = actualproxy['name']
            configuredproxy = self._lookup_by_name('httpproxies', name)
            if not configuredproxy:
                pgwservice.schedule_action('remove_http_proxy', args={'name': name}).wait(die=True)
                toremoveforwards.append(name)
            else:
                tobeconfigured.remove(configuredproxy)

        gwinfo = gwservice.schedule_action('info').wait(die=True).result
        usedports = set()
        for actualforward in gwinfo['portforwards']:
            removed = False
            for fwdname in toremoveforwards:
                if actualforward['name'].startswith('proxy_{}'.format(fwdname)):
                    gwservice.schedule_action('remove_portforward', args={'name': actualforward['name']}).wait(die=True)
                    removed = True
                    break
            if not removed:
                usedports.add(actualforward['srcport'])

        # Add proxies
        vmips = {}
        for proxy in tobeconfigured:
            pproxy = {
                'host': proxy['host'],
                'types': proxy['types'],
                'name': proxy['name'],
                'destinations': [],
            }
            fwdnames = []
            for destination in proxy['destinations']:
                vmname = destination['vm']
                if vmname not in vmips:
                    vmips[vmname] = self._get_vm_ip(vmname)
                port = BASEPORT
                while port in usedports:
                    port += 1
                usedports.add(port)
                fwdname = 'proxy_{}_{}'.format(proxy['name'], vmname)
                forward = {
                    'name': fwdname,
                    'srcport': port,
                    'srcnetwork': 'publicgw',
                    'dstip': vmips[vmname],
                    'dstport': destination['port'],
                    'protocols': ['tcp'],
                }
                gwservice.schedule_action('add_portforward', args={'forward': forward}).wait(die=True)
                fwdnames.append(fwdname)
                pproxy['destinations'].append('http://{}:{}'.format(ztip, port))
            try:
                pgwservice.schedule_action('add_http_proxy', args={'proxy': pproxy}).wait(die=True)
            except:
                for fwd in fwdnames:
                    gwservice.schedule_action('remove_portforward', args={'name': fwd}).wait(die=True)
                raise

    def _get_vm_ip(self, vm):
        vmservice = self.api.services.get(name=vm, template_uid=DM_VM_UID)
        info = vmservice.schedule_action('info').wait(die=True).result
        for network in self.data['networks']:
            if network['type'] == 'zerotier' and network['id'] == info['zerotier']['id']:
                break
        else:
            raise LookupError('Gateway is not part of the same Zerotier as the VM {}'.format(vm))
        zcl = j.clients.zerotier.get(info['zerotier']['ztClient'], interactive=False)
        network = zcl.network_get(info['zerotier']['id'])
        member = network.member_get(info['ztIdentity'].split(':')[0])
        return member.private_ip

    def info(self):
        pgw_info = self._get_pgw_service().schedule_action('info').wait(die=True).result
        data = {
            'publicip': pgw_info['publicip'],
            'networks': self.data['networks'],
            'httpproxies': self.data['httpproxies'],
            'portforwards': self.data['portforwards'],
        }
        return data

    def add_portforward(self, forward):
        forward['protocols'] = forward.get('protocols', ['tcp'])
        self.data.setdefault('portforwards', []).append(forward)
        try:
            self._update_portforwards()
        except:
            self.data['portforwards'].remove(forward)
            raise

    def remove_portforward(self, name):
        forward = self._lookup_by_name('portforwards', name)
        if forward:
            self.data['portforwards'].remove(forward)
            self._update_portforwards()

    def add_http_proxy(self, proxy):
        self.data.setdefault('httpproxies', []).append(proxy)
        try:
            self._update_proxies()
        except:
            self.data['httpproxies'].remove(proxy)
            raise

    def remove_http_proxy(self, name):
        proxy = self._lookup_by_name('httpproxies', name)
        if proxy:
            self.data['httpproxies'].remove(proxy)
            self._update_proxies()

    def add_network(self, network):
        if network.get('public'):
            raise ValueError('Can not add public networks')
        self._get_gw_service().schedule_action('add_network', args={'network': network}).wait(die=True)
        self.data['networks'].append(network)

    def remove_network(self, name):
        self._get_gw_service().schedule_action('remove_network', args={'name': name}).wait(die=True)
        for network in self.data['networks']:
            if network['name'] == name:
                self.data['networks'].remove(network)
                return

    def uninstall(self):
        try:
            gwservice = self._get_gw_service()
        except:
            pass
        else:
            gwservice.delete()
        try:
            pgwservice = self._get_pgw_service()
        except:
            pass
        else:
            pgwservice.delete()
        for network in self.data['networks']:
            if network['type'] == 'zerotier' and network.get('ztClient'):
                zerotierservice = self.api.services.get(name=network['ztClient'])
                data = {'url': self._robot_url, 'serviceguid': self.guid}
                zerotierservice.schedule_action('remove_from_robot', args=data).wait(die=True)
