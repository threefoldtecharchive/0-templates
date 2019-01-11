from copy import deepcopy

import gevent
from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry
from zerorobot.template.state import StateCheckError

ETCD_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/etcd/0.0.1'
ZT_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/zerotier_client/0.0.1'


class EtcdCluster(TemplateBase):

    version = '0.0.1'
    template_name = "etcd_cluster"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.add_delete_callback(self.uninstall)
        self.recurring_action('_monitor', 30)  # every 30 seconds
        self.recurring_action('_ensure_etcds_connections', 300)

        self._farm = j.sal_zos.farm.get(self.data['farmerIyoOrg'])
        self._robots = {}

    def validate(self):
        self.state.delete('status', 'running')
        for nic in self.data['nics']:
            if nic['type'] == 'zerotier':
                break
        else:
            raise ValueError('Service must contain at least one zerotier nic')

        if not self.data['farmerIyoOrg']:
            raise ValueError('Invalid value for farmerIyoOrg')

        self.data['password'] = self.data['password'] if self.data['password'] else j.data.idgenerator.generateXCharID(
            16)
        self.data['token'] = self.data['token'] if self.data['token'] else self.guid

    def _nodes(self):
        nodes = self._farm.filter_online_nodes()
        if not nodes:
            raise ValueError('There are no online nodes in this farm')
        return nodes

    def _monitor(self):
        try:
            self.state.check('actions', 'start', 'ok')
        except StateCheckError:
            return

        for etcd in self.data['etcds']:
            robot = self.api.robots.get(etcd['node'], etcd['url'])
            service = robot.services.get(template_uid=ETCD_TEMPLATE_UID, name=etcd['name'])
            try:
                service.state.check('status', 'running', 'ok')
            except StateCheckError:
                self.state.set('status', 'running', 'error')
                return
        self.state.set('status', 'running', 'ok')

    def _ensure_etcds_connections(self):
        try:
            self.state.check('actions', 'install', 'ok')
        except StateCheckError:
            return

        self.logger.info("verify etcds connections")

        # gather all the etcd services
        etcds = []
        for etcd in self.data['etcds']:
            robot = self.api.robots.get(etcd['node'], etcd['url'])
            etcds.append(robot.services.get(template_uid=ETCD_TEMPLATE_UID, name=etcd['name']))

        connection = cluster_connection(etcds)
        if not self.data.get('clusterConnections'):
            self.data['clusterConnections'] = connection

        if connection != self.data['clusterConnections']:
            for etcd in etcds:
                etcd.schedule_action('update_cluster', args={'cluster': connection}).wait(die=True)
        self.data['clusterConnections'] = connection

    def _deploy_etcd_cluster(self):
        self.logger.info('create etcds for the etcd cluster')
        deployed_etcds = []

        if self.data['etcds']:
            for etcd in self.data['etcds']:
                robot = self.api.robots.get(etcd['node'], etcd['url'])
                service = robot.services.get(template_uid=ETCD_TEMPLATE_UID, name=etcd['name'])
                deployed_etcds.append(service)

        self.logger.info('etcds required: {}'.format(self.data['nrEtcds']))
        self.logger.info('etcds already deployed {}'.format(len(self.data['etcds'])))
        required_nr_etcds = self.data['nrEtcds'] - len(deployed_etcds)
        for etcd, node in self._deploy_etcds(required_nr_etcds):
            deployed_etcds.append(etcd)
            self.data['etcds'].append({'name': etcd.name,
                                       'url': node['robot_address'],
                                       'node': node['node_id']})
            deployed_nr_etcd = len(deployed_etcds)
            self.logger.info('{} etcds deployed, remaining {}'.format(
                deployed_nr_etcd, required_nr_etcds - deployed_nr_etcd))
            self.save()
        if len(deployed_etcds) < self.data['nrEtcds']:
            raise RuntimeError('Could not deploy enough etcds for cluster')

        return deployed_etcds

    def _deploy_etcds(self, required_etcds):
        nodes = list(self._nodes())
        nr_deployed_etcds = 0
        etcds = []
        while nr_deployed_etcds < required_etcds:
            for i in range(required_etcds - nr_deployed_etcds):
                self.logger.info('number of possible nodes to use for namespace deployments %s', len(nodes))
                if len(nodes) <= 0:
                    return etcds
                node = nodes[i % len(nodes)]
                self.logger.info("try to install etcd on node %s" % node['node_id'])
                try:
                    etcds.append(self._install_etcd(node))
                    nr_deployed_etcds += 1
                except:
                    nodes.remove(node)
        return etcds

        # gls = set()
        # for i in range(required_etcds - nr_deployed_etcds):
        #     node = nodes[i % len(nodes)]
        #     self.logger.info("try to install etcd on node %s" % node['node_id'])
        #     gls.add(gevent.spawn(self._install_etcd, node=node))

        # for g in gevent.iwait(gls):
        #     if g.exception and g.exception.node in nodes:
        #         self.logger.error("we could not deploy on node %s, remove it from the possible node to use", node['node_id'])
        #         nodes.remove(g.exception.node)
        #     else:
        #         etcd, node = g.value
        #         nr_deployed_etcds += 1
        #         yield (etcd, node)

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

    def _install_etcd(self, node):
        robot = self.api.robots.get(node['node_id'], node['robot_address'])
        try:
            nics = self._create_zt_clients(self.data['nics'], node['robot_address'])
            data = {
                'token': self.data['token'],
                'password': self.data['password'],
                'nics': nics,
                'hostNetwork': self.data.get('hostNetwork', False),
            }
            etcd = robot.services.create(template_uid=ETCD_TEMPLATE_UID, data=data)
            task = etcd.schedule_action('install').wait(timeout=300)
            if task.eco:
                etcd.delete()
                self._remove_zt_clients(self.data['nics'], node['robot_address'])
                raise EtcdDeployError(task.eco.message, node)
            return etcd, node

        except Exception as err:
            raise EtcdDeployError(str(err), node)

    def install(self):
        self.logger.info('Installing etcd cluster {}'.format(self.name))
        etcds = self._deploy_etcd_cluster()
        self.data['clusterConnections'] = cluster_connection(etcds)
        tasks = list()
        for etcd in etcds:
            self.logger.info("update cluster config on %s" % etcd.name)
            tasks.append(etcd.schedule_action('update_cluster', args={'cluster': self.data['clusterConnections']}))
            tasks.append(etcd.schedule_action('start'))
        for task in tasks:
            task.wait(die=True)

        @retry(Exception, tries=4, delay=3, backoff=2)
        def config():
            etcd = etcds[0]
            self.logger.info("configure etcd authentication")
            etcd.schedule_action('_enable_auth').wait(die=True)
            self.logger.info("configure traefik entry")
            etcd.schedule_action('_prepare_traefik').wait(die=True)
        config()

        self.state.set('actions', 'install', 'ok')
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def uninstall(self):
        # uninstall and delete all the created etcds
        def delete_etcd(etcd):
            self.logger.info("deleting etcd %s on node %s", etcd['node'], etcd['url'])
            robot = self.api.robots.get(etcd['node'], etcd['url'])
            try:
                self._remove_zt_clients(self.data['nics'], etcd['url'])
                service = robot.services.get(template_uid=ETCD_TEMPLATE_UID, name=etcd['name'])
                service.schedule_action('uninstall').wait(die=True)
                service.delete()
            except ServiceNotFoundError:
                pass

            if etcd in self.data['etcds']:
                self.data['etcds'].remove(etcd)

        for etcd in list(self.data['etcds']):
            delete_etcd(etcd)
        # group = gevent.pool.Group()
        # group.imap_unordered(delete_etcd, self.data['etcds'])
        # group.join()
        self.data['clusterConnections'] = None

        self.state.delete('actions', 'install')
        self.state.delete('status', 'running')

    def start(self):
        tasks = []
        for etcd in self.data['etcds']:
            robot = self.api.robots.get(etcd['node'], etcd['url'])
            etcd = robot.services.get(template_uid=ETCD_TEMPLATE_UID, name=etcd['name'])
            tasks.append(etcd.schedule_action('start'))

        for task in tasks:
            task.wait(die=True)

        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def stop(self):
        tasks = []
        for etcd in self.data['etcds']:
            robot = self.api.robots.get(etcd['node'], etcd['url'])
            etcd = robot.services.get(template_uid=ETCD_TEMPLATE_UID, name=etcd['name'])
            tasks.append(etcd.schedule_action('stop'))

        for task in tasks:
            task.wait(die=True)

        self.state.delete('actions', 'start')
        self.state.delete('status', 'running')

    def connection_info(self):
        etcds = []
        for etcd in self.data['etcds']:
            robot = self.api.robots.get(etcd['node'], etcd['url'])
            etcds.append(robot.services.get(template_uid=ETCD_TEMPLATE_UID, name=etcd['name']))
        connections = etcds_connection(etcds)
        return {
            'user': 'root',
            'password': self.data['password'],
            'etcds': connections,
        }


def cluster_connection(etcds):
    connections = etcds_connection(etcds)
    return ','.join(sorted([connection['cluster_entry'] for connection in connections]))


def etcds_connection(etcds):
    tasks = map(lambda etcd: etcd.schedule_action('connection_info'), etcds)
    result = map(lambda task: task.wait(die=True).result, tasks)
    return list(result)


class EtcdDeployError(RuntimeError):
    def __init__(self, msg, node):
        super().__init__(self, msg)
        self.node = node
