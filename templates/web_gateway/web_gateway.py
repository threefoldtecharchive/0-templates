import gevent
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
        self.recurring_action('_monitor', 30)  # every 30 seconds
        self._traefik_api = None
        self._traefik_url = None
        self._coredns_api = None
        self._coredns_url = None

    def validate(self):
        self.state.delete('status', 'running')
        for nic in self.data['nics']:
            if nic['type'] == 'zerotier':
                break
        else:
            raise ValueError('Service must contain at least one zerotier nic')

        for key in ['farmerIyoOrg', 'nrEtcds', 'traefikNode', 'corednsNode']:
            if not self.data[key]:
                raise ValueError('Invalid value for {}'.format(key))
            
        # capacity = j.clients.threefold_directory.get(interactive=False)

        # try:
        #     node, _ = capacity.api.GetCapacity(self.data['traefikNode'])
        #     self._traefik_api = self.api.robots.get(self.data['traefikNode'], node.robot_address)
        #     self._traefik_url = node.robot_address
        # except HTTPError as err:
        #     if err.response.status_code == 404:
        #         raise ValueError('Traefik node {} does not exist'.format(self.data['traefikNode']))
        #     raise err
    
        # try:
        #     node, _ = capacity.api.GetCapacity(self.data['corednsNode'])
        #     self._coredns_api = self.api.robots.get(self.data['corednsNode'], node.robot_address)
        #     self._coredns_url = node.robot_address
        # except HTTPError as err:
        #     if err.response.status_code == 404:
        #         raise ValueError('Coredns node {} does not exist'.format(self.data['corednsNode']))
        #     raise err
        
        # @todo remove testing hack
        self._traefik_api = self.api.robots.get('local', 'http://localhost:6600')
        self._traefik_url = 'http://localhost:6600'
        self._coredns_api = self.api.robots.get('local', 'http://localhost:6600')
        self._coredns_url = 'http://localhost:6600'

        self.data['etcdPassword'] = self.data['etcdPassword'] if self.data['etcdPassword'] else j.data.idgenerator.generateXCharID(16)

    @property
    def _etcd_cluster(self):
        return self.api.services.get(template_uid=ETCD_CLUSTER_TEMPLATE_UID, name=self.guid)

    @property
    def _traefik(self):
        return self._traefik_api.services.get(template_uid=TRAEFIK_TEMPLATE_UID, name=self.guid)
    
    @property
    def _coredns(self):
        return self._coredns_api.services.get(template_uid=COREDNS_TEMPLATE_UID, name=self.guid)

    def install(self):
        self.logger.info('Installing web gateway {}'.format(self.name))
        self.logger.info('Installing etcd cluster')
        cluster_data = {
            'nrEtcds': self.data['nrEtcds'],
            'password': self.data['etcdPassword'],
            'farmerIyoOrg': self.data['farmerIyoOrg'],
            'nics': self.data['nics'],
        }
        etcd_cluster = self.api.services.find_or_create(ETCD_CLUSTER_TEMPLATE_UID, self.guid, cluster_data)
        etcd_cluster.schedule_action('install').wait(die=True)
        cluster_connection = etcd_cluster.schedule_action('connection_info').wait(die=True)

        traefik_endpoint = ','.join(['{}:{}'.format(connection['ip'], connection['port']) for connection in cluster_connection['etcds']])
        coredns_endpoint = ' '.join([connection['client_url'] for connection in cluster_connection['etcds']])
        self._install_traefik(traefik_endpoint)
        self._install_coredns(coredns_endpoint)

        self.state.set('actions', 'install', 'ok')
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')
    
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

    def _install_traefik(self, traefik_endpoint):
        self.logger.info('Installing traefik')
        nics = self._create_zt_clients(self.data['nics'], self._traefik_url)
        data = {
            'etcdEndpoint': traefik_endpoint,
            'etcdPassword': self.data['etcdPassword'],
            'etcdWatch': self.data['etcdWatch'],
            'nics': nics,
        }
        traefik = self._traefik_api.services.find_or_create(TRAEFIK_TEMPLATE_UID, self.guid, data)
        traefik.schedule_action('install').wait(die=True)

    def _install_coredns(self, coredns_endpoint):
        self.logger.info('Installing coredns')
        nics = self._create_zt_clients(self.data['nics'], self._coredns_url)
        data = {
            'etcdEndpoint': coredns_endpoint,
            'etcdPassword': self.data['etcdPassword'],
            'nics': nics,
        }
        coredns = self._coredns_api.services.find_or_create(COREDNS_TEMPLATE_UID, self.guid, data)
        coredns.schedule_action('install').wait(die=True)
    
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
        
    def _uninstall_traefik(self):
        self._remove_zt_clients(self.data['nics'], self._traefik_url)
        try:
            self._traefik.schedule_action('uninstall').wait(die=True)
            self._traefik.delete()
        except ServiceNotFoundError:
            pass

    def _uninstall_coredns(self):
        self._remove_zt_clients(self.data['nics'], self._coredns)
        try:
            self._coredns.schedule_action('uninstall').wait(die=True)
            self._coredns.delete()
        except ServiceNotFoundError:
            pass

    def uninstall(self):
        try:
            self._etcd_cluster.schedule_action('uninstall').wait(die=True)
            self._etcd_cluster.delete()
        except ServiceNotFoundError:
            pass
        
        self._uninstall_traefik()
        self._uninstall_coredns()
