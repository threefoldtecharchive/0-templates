import gevent
from jumpscale import j

from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError
from zerorobot.service_collection import ServiceNotFoundError


ETCD_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/etcd/0.0.1'


class EtcdCluster(TemplateBase):

    version = '0.0.1'
    template_name = "etcd_cluster"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        # self.add_delete_callback(self.uninstall)
        # self.recurring_action('_monitor', 30)  # every 30 seconds
        self._robots = {}


    def validate(self):
        self.state.delete('status', 'running')
        for nic in self.data['nics']:
            if nic['type'] == 'zerotier':
                break
        else:
            raise ValueError('Service must contain at least one zerotier nic')
        
        for key in ['token', 'farmerIyoOrg']:
            if not self.data[key]:
                raise ValueError('Invalid value for {}'.format(key))

        self.data['password'] = self.data['password'] if self.data['password'] else j.data.idgenerator.generateXCharID(10)

    @property
    def _farm(self):
        return j.sal_zos.farm(self.data['farmIyoOrg'])

    def _nodes(self):
        # @todo remove testing hack when done
        return [{'node_id': 'local', 'robot_address': 'http://localhost:6600'}]
        # keep a cache for a few minutes
        nodes = self._farm.list_nodes()
        if not nodes:
            raise ValueError('There are no nodes in this farm')
        nodes = self._farm.filter_online_nodes() 
        if not nodes:
            raise ValueError('There are no online nodes in this farm')
        return nodes

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
            self.logger.info('{} etcds deployed, remaining {}'.format(deployed_nr_etcd, required_nr_etcds - deployed_nr_etcd))
            self.save()
        if len(deployed_etcds) < self.data['nrEtcds']:
            raise RuntimeError('Could not deploy enough etcds for cluster')
        
        return deployed_etcds
        
    def _deploy_etcds(self, required_etcds):
        nodes = self._nodes().copy()
        nr_deployed_etcds = 0
        while nr_deployed_etcds < required_etcds:
            self.logger.info('number of possible nodes to use for namespace deployments %s', len(nodes))
            if len(nodes) <= 0:
                return
            
            gls = set()
            for i in range(required_etcds - nr_deployed_etcds):
                node = nodes[i % len(nodes)]
                self.logger.info("try to install etcd on node %s" % node['node_id'])
                gls.add(gevent.spawn(self._install_etcd, node=node))

            for g in gevent.iwait(gls):
                if g.exception and g.exception.node in nodes:
                    self.logger.error("we could not deploy on node %s, remove it from the possible node to use", node['node_id'])
                    nodes.remove(g.exception.node)
                else:
                    etcd, node = g.value
                    nr_deployed_etcds += 1
                    yield (etcd, node)

    def _install_etcd(self, node):
        robot = self.api.robots.get(node['node_id'], node['robot_address'])
        robot = self.api.robots.get('local')
        try:
            data = {
                'token': self.data['token'],
                'password': self.data['password'],
                'nics': self.data['nics'],
            }
            etcd = robot.services.create(template_uid=ETCD_TEMPLATE_UID, data=data)
            task = etcd.schedule_action('install').wait(timeout=300)
            if task.eco:
                etcd.delete()
                raise EtcdDeployError(task.eco.message, node)
            return etcd, node

        except Exception as err:
            raise EtcdDeployError(str(err), node)

    def install(self):
        self.logger.info('Installing etcd cluster {}'.format(self.name))
        etcds = self._deploy_etcd_cluster()
        cluster_connection = ','.join(etcds_cluster_connection(etcds))
        self.data['clusterConnections'] = cluster_connection

        tasks = list()
        for etcd in etcds:
            tasks.append(etcd.schedule_action('update_cluster', args={'cluster': cluster_connection}))
            tasks.append(etcd.schedule_action('start'))
        for task in tasks:
            task.wait(die=True)
        self.state.set('actions', 'install', 'ok')
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def uninstall(self):
        # uninstall and delete all the created namespaces
        def delete_etcd(etcd):
            self.logger.info("deleting etcd %s on node %s", etcd['node'], etcd['url'])
            robot = self.api.robots.get(etcd['node'], etcd['url'])
            try:
                service = robot.services.get(template_uid=ETCD_TEMPLATE_UID, name=etcd['name'])
                service.schedule_action('uninstall').wait(die=True)
                service.delete()
            except ServiceNotFoundError:
                pass

            if etcd in self.data['etcds']:
                self.data['etcds'].remove(etcd)

        group = gevent.pool.Group()
        group.imap_unordered(delete_etcd, self.data['etcds'])
        group.join()
        self.data['clusterConnections'] = None

        self.state.delete('actions', 'install')
        self.state.delete('status', 'running')

def etcds_cluster_connection(etcds):
    # group = gevent.pool.Group()
    # return list(group.imap_unordered(etcd_cluster_connection, etcds))
    for etcd in etcds:
        yield(etcd_cluster_connection(etcd))



def etcd_cluster_connection(etcd):
    result = etcd.schedule_action('connection_info').wait(die=True).result
    # if there is not special storage network configured,
    # then the sal return the zerotier as storage address
    return '{}={}'.format(etcd.guid, result['peer_url'])


class EtcdDeployError(RuntimeError):
    def __init__(self, msg, node):
        super().__init__(self, msg)
        self.node = node
