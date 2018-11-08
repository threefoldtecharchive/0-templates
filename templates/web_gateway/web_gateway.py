import gevent
import json
from copy import deepcopy
from requests import HTTPError

from jumpscale import j

from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError
from zerorobot.service_collection import ServiceNotFoundError


ETCD_CLUSTER_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/etcd_cluster/0.0.1'
TRAEFIK_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/traefik/0.0.1'
ZT_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/zerotier_client/0.0.1'
COREDNS_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/coredns/0.0.1'


class WebGateway(TemplateBase):

    version = '0.0.1'
    template_name = 'web_gateway'

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.add_delete_callback(self.uninstall)
        self._public_api = None
        self._public_url = None
        self._etcds_name = 'etcds_%s' % self.guid
        self._coredns_name = "coredns_%s" % self.guid
        self._traefik_name = "traefik_%s" % self.guid
        self.recurring_action('_monitor', 30)  # every 30 seconds

    def _monitor(self):
        self.logger.info('Monitor web gateway %s' % self.name)
        self.state.check('actions', 'start', 'ok')
        try:
            self._etcd_cluster.state.check('status','running','ok')
            self._traefik.state.check('status','running','ok')
            self._coredns.state.check('status','running','ok')
            self.state.set('status', 'running', 'ok')
        except StateCheckError:
            self.state.delete('status', 'running')

        cluster_connection = self._etcd_cluster.schedule_action('connection_info').wait(die=True).result
        if self.data['etcdConnectionInfo']['etcds'] != cluster_connection['etcds']:
            self.data['etcdConnectionInfo']['etcds'] = cluster_connection['etcds']
            traefik_endpoint = ','.join(['{}:{}'.format(connection['ip'], connection['client_port']) for connection in self.data['etcdConnectionInfo']['etcds']])
            coredns_endpoint = ' '.join([connection['client_url'] for connection in self.data['etcdConnectionInfo']['etcds']])
            self._coredns.schedule_action('update_endpoint', args=coredns_endpoint).wait(die=True)
            self._traefik.schedule_action('update_endpoint', args=traefik_endpoint).wait(die=True)

    def validate(self):
        for nic in self.data['nics']:
            if nic['type'] == 'zerotier':
                break
        else:
            raise ValueError('Service must contain at least one zerotier nic')

        for key in ['farmerIyoOrg', 'nrEtcds', 'publicNode']:
            if not self.data[key]:
                raise ValueError('Invalid value for {}'.format(key))

        self.data['etcdPassword'] = self.data['etcdPassword'] if self.data['etcdPassword'] else j.data.idgenerator.generateXCharID(16)

        try:
            self.state.check('actions', 'install', 'ok')
            self._public_api = self.api.robots.get(self.data['publicNode'])
            self._public_url = self._public_api._client.config.data['url']
            return
        except:
            pass
            # the rest of the logic is only when the node is not yet installed

        capacity = j.clients.threefold_directory.get(interactive=False)

        try:
            node, _ = capacity.api.GetCapacity(self.data['publicNode'])
            self._public_api = self.api.robots.get(self.data['publicNode'], node.robot_address)
            self._public_url = node.robot_address
        except HTTPError as err:
            if err.response.status_code == 404:
                raise ValueError('Node {} does not exist'.format(self.data['publicNode']))
            raise err

    @property
    def _etcd_cluster(self):
        return self.api.services.get(template_uid=ETCD_CLUSTER_TEMPLATE_UID, name=self._etcds_name)

    @property
    def _traefik(self):
        return self._public_api.services.get(template_uid=TRAEFIK_TEMPLATE_UID, name=self._traefik_name)

    @property
    def _coredns(self):
        return self._public_api.services.get(template_uid=COREDNS_TEMPLATE_UID, name=self._coredns_name)

    def install(self):
        self.logger.info('Installing web gateway {}'.format(self.name))
        self.data['etcdConnectionInfo'] = self._install_etcd_cluster()
        
        if not self.data['etcdConnectionInfo']['etcds']:
            raise RuntimeError('Failed to retrieve etcd cluster etcd connections')
        
        traefik_endpoint = ','.join(['{}:{}'.format(connection['ip'], connection['client_port']) for connection in self.data['etcdConnectionInfo']['etcds']])
        coredns_endpoint = ' '.join([connection['client_url'] for connection in self.data['etcdConnectionInfo']['etcds']])

        self._install_traefik(traefik_endpoint)
        self._install_coredns(coredns_endpoint)
        self._set_public_ips(self.data['etcdConnectionInfo'])

        self.state.set('actions', 'install', 'ok')
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def _set_public_ips(self, cluster_connection):
        """
        Create the etcd client and webgateway sal instance and set the public ips
        """
        for etcd in cluster_connection['etcds']:
            j.clients.etcd.get(self._etcds_name, data={'host': etcd['ip'], 'port': etcd['client_port'], 'user': cluster_connection['user'], 'password_': cluster_connection['password']})
            break
        j.sal.webgateway.get(self.name, data={'etcd_instance': self._etcds_name, 'public_ips': self.data['publicIps']})

    def _create_zt_clients(self, nics, node_url):
        result = deepcopy(nics)
        for nic in result:
            zt_name = nic['ztClient']
            zt_client = self.api.services.get(name=zt_name, template_uid=ZT_TEMPLATE_UID)
            node_zt_name = '{}_{}'.format(zt_name, self.guid)
            data = {'url': node_url, 'name': node_zt_name}
            zt_client.schedule_action('add_to_robot', args=data).wait(die=True)
            nic['ztClient'] = node_zt_name

        return result

    def _remove_zt_clients(self, nics, node_url):
        for nic in nics:
            zt_name = nic['ztClient']
            zt_client = self.api.services.get(name=zt_name, template_uid=ZT_TEMPLATE_UID)
            node_zt_name = '{}_{}'.format(zt_name, self.guid)
            data = {'url': node_url, 'name': node_zt_name}
            zt_client.schedule_action('remove_from_robot', args=data).wait(die=True)

    def _install_etcd_cluster(self):
        self.logger.info('Installing etcd cluster')
        cluster_data = {
            'nrEtcds': self.data['nrEtcds'],
            'password': self.data['etcdPassword'],
            'farmerIyoOrg': self.data['farmerIyoOrg'],
            'nics': self.data['nics'],
        }
        etcd_cluster = self.api.services.find_or_create(ETCD_CLUSTER_TEMPLATE_UID, self._etcds_name, cluster_data)
        etcd_cluster.schedule_action('install').wait(die=True)
        cluster_connection = etcd_cluster.schedule_action('connection_info').wait(die=True).result
        return cluster_connection

    def _install_traefik(self, traefik_endpoint):
        self.logger.info('Installing traefik')
        nics = self._create_zt_clients(self.data['nics'], self._public_url)
        data = {
            'etcdEndpoint': traefik_endpoint,
            'etcdPassword': self.data['etcdPassword'],
            'etcdWatch': True,
            'nics': nics,
        }
        traefik = self._public_api.services.find_or_create(TRAEFIK_TEMPLATE_UID, self._traefik_name, data)
        traefik.schedule_action('install').wait(die=True)
        traefik.schedule_action('start').wait(die=True)

    def _install_coredns(self, coredns_endpoint):
        self.logger.info('Installing coredns')
        nics = self._create_zt_clients(self.data['nics'], self._public_url)
        data = {
            'etcdEndpoint': coredns_endpoint,
            'etcdPassword': self.data['etcdPassword'],
            'nics': nics,
        }
        coredns = self._public_api.services.find_or_create(COREDNS_TEMPLATE_UID, self._coredns_name, data)
        coredns.schedule_action('install').wait(die=True)
        coredns.schedule_action('start').wait(die=True)

    def start(self):
        self.state.check('actions', 'install', 'ok')
        self._etcd_cluster.schedule_action('start').wait(die=True)
        self._traefik.schedule_action('start').wait(die=True)
        self._coredns.schedule_action('start').wait(die=True)
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def stop(self):
        self.state.check('actions', 'install', 'ok')
        self._etcd_cluster.schedule_action('stop').wait(die=True)
        self._traefik.schedule_action('stop').wait(die=True)
        self._coredns.schedule_action('stop').wait(die=True)
        self.state.delete('actions', 'start')
        self.state.delete('status', 'running')

    def _uninstall_etcd_cluster(self):
        try:
            self._etcd_cluster.schedule_action('uninstall').wait(die=True)
            self._etcd_cluster.delete()
        except ServiceNotFoundError:
            pass

    def _uninstall_traefik(self):
        self._remove_zt_clients(self.data['nics'], self._public_url)
        try:
            self._traefik.schedule_action('uninstall').wait(die=True)
            self._traefik.delete()
        except ServiceNotFoundError:
            pass

    def _uninstall_coredns(self):
        self._remove_zt_clients(self.data['nics'], self._public_url)
        try:
            self._coredns.schedule_action('uninstall').wait(die=True)
            self._coredns.delete()
        except ServiceNotFoundError:
            pass

    def uninstall(self):
        self._uninstall_etcd_cluster()
        self._uninstall_traefik()
        self._uninstall_coredns()

    def connection_info(self):
        self.state.check('status', 'running', 'ok')
        cluster = self._etcd_cluster.schedule_action('connection_info').wait(die=True).result
        return {
            'etcd_cluster': cluster,
            'public_ips': self.data['publicIps']
        }
