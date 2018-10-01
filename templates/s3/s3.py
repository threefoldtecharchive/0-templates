import math
import time

import requests

import gevent
import netaddr
from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import timeout
from zerorobot.template.state import StateCheckError

VM_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/dm_vm/0.0.1'
GATEWAY_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/gateway/0.0.1'
MINIO_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/minio/0.0.1'
NS_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/namespace/0.0.1'


class S3(TemplateBase):
    version = '0.0.1'
    template_name = "s3"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.recurring_action('_monitor', 60)  # every 30 seconds
        self.recurring_action('_ensure_namespaces_connections', 300)
        self.recurring_action('_update_url', 300)

        self._robots = {}

    def validate(self):
        if self.data['parityShards'] > self.data['dataShards']:
            raise ValueError('parityShards must be equal to or less than dataShards')

        if len(self.data['minioPassword']) < 8:
            raise ValueError("minio password need to be at least 8 characters")

        if not self.data['nsPassword']:
            self.data['nsPassword'] = j.data.idgenerator.generateXCharID(32)

    @property
    def _nodes(self):
        # keep a cache for a few minutes
        nodes = list_farm_nodes(self.data['farmerIyoOrg'])
        if not nodes:
            raise ValueError('There are no nodes in this farm')
        return nodes

    @timeout(60)
    def _update_url(self):
        try:
            self.state.check('status', 'running', 'ok')
        except StateCheckError:
            return

        self.logger.info("update minio urls")
        vm_robot, public_ip = self._vm_robot_and_ip()
        minio = vm_robot.services.get(template_uid=MINIO_TEMPLATE_UID, name=self.guid)
        public_port = minio.schedule_action('node_port').wait(die=True).result

        vm_info = self._vm().schedule_action('info').wait(die=True, timeout=30).result
        storage_ip = vm_info['host']['storage_addr']
        storage_port = None
        for src, dest in vm_info['ports'].items():
            if dest == public_port:
                storage_port = int(src)
                break

        self.data['minioUrls'] = {
            'public': 'http://{}:{}'.format(public_ip, public_port),
            'storage': '',
        }
        if storage_ip and storage_port:
            self.data['minioUrls']['storage'] = 'http://{}:{}'.format(storage_ip, storage_port)

        return self.data['minioUrls']

    def _ensure_namespaces_connections(self):
        try:
            self.state.check('actions', 'install', 'ok')
        except StateCheckError:
            return

        self.logger.info("verify data backend namespace connections")

        zdbs_connection = []
        # gather all the namespace services
        namespaces = []
        for namespace in self.data['namespaces']:
            robot = get_zrobot(namespace['node'], namespace['url'])
            namespaces.append(robot.services.get(template_uid=NS_TEMPLATE_UID, name=namespace['name']))

        namespaces_connection = sorted(namespaces_connection_info(namespaces))
        if not self.data.get('current_namespaces_connections'):
            self.data['current_namespaces_connections'] = sorted(namespaces_connection)

        vm_robot, _ = self._vm_robot_and_ip()
        minio = vm_robot.services.get(template_uid=MINIO_TEMPLATE_UID, name=self.guid)

        if namespaces_connection == sorted(self.data['current_namespaces_connections']):
            self.logger.info("namespace connection in service data are in sync with reality")
        else:
            self.logger.info("some namespace connection in service data are not correct, updating minio configuration")
            # calling update_zerodbs will also tell minio process to reload its config
            minio.schedule_action('update_zerodbs', args={'zerodbs': namespaces_connection}).wait(die=True)
            self.data['current_namespaces_connections'] = namespaces_connection

        self.logger.info("verify tlog namespace connections")
        if 'tlog' not in self.data or not self.data['tlog'].get('node') or not self.data['tlog'].get('node'):
            return

        robot = get_zrobot(self.data['tlog']['node'], self.data['tlog']['url'])
        namespace = robot.services.get(template_uid=NS_TEMPLATE_UID, name=self.data['tlog']['name'])

        connection_info = namespace_connection_info(namespace)
        if self.data['tlog'].get('address') and self.data['tlog']['address'] == connection_info:
            self.logger.info("tlog namespace connection in service data is in sync with reality")
            return

        self.logger.info("tlog namespace connection in service data is not correct, updating minio configuration")
        t = minio.schedule_action('update_tlog', args={'namespace': self.guid+'_tlog',
                                                       'address': connection_info})
        t.wait(die=True)
        self.data['tlog']['address'] = connection_info

    def _monitor(self):
        try:
            self.state.check('actions', 'install', 'ok')
        except StateCheckError:
            return
        self.logger.info('Monitor s3 %s' % self.name)

        @timeout(10)
        def update_state():
            vm_robot, _ = self._vm_robot_and_ip()
            minio = vm_robot.services.get(template_uid=MINIO_TEMPLATE_UID, name=self.guid)
            try:
                minio.state.check('status', 'running', 'ok')
                self.state.set('status', 'running', 'ok')
                return
            except StateCheckError:
                self.state.delete('status', 'running')
                zdbs_connection = []
                for namespace in self.data['namespaces']:
                    robot = get_zrobot(namespace['node'], namespace['url'])
                    ns = robot.services.get(template_uid=NS_TEMPLATE_UID, name=namespace['name'])
                    try:
                        ns.state.check('status', 'running', 'ok')
                        zdbs_connection.append(namespace_connection_info(ns))
                    except StateCheckError:
                        break
                else:
                    minio = vm_robot.services.get(template_uid=MINIO_TEMPLATE_UID, name=self.guid)
                    minio.schedule_action('update_zerodbs', args={'zerodbs': zdbs_connection}).wait(die=True)

        try:
            update_state()
        except:
            self.state.delete('status', 'running')

    def install(self):
        def deploy_data_namespaces():
            namespaces = self._deploy_minio_backend_namespaces()
            namespaces_connections = namespaces_connection_info(namespaces)
            return namespaces_connections

        def deploy_tlog_namespace():
            namespace = self._deploy_minio_tlog_namespace()
            return namespace_connection_info(namespace)

        def deploy_vm():
            self._deploy_minio_vm()
            return self._vm_robot_and_ip()

        # deploy all namespaces and vm concurrently
        ns_data_gl = gevent.spawn(deploy_data_namespaces)
        ns_tlog_gl = gevent.spawn(deploy_tlog_namespace)
        vm_gl = gevent.spawn(deploy_vm)
        self.logger.info("wait for all namespaces and vm to be installed")
        gevent.wait([ns_data_gl, ns_tlog_gl, vm_gl])

        if ns_data_gl.exception:
            raise ns_data_gl.exception
        namespaces_connections = ns_data_gl.value
        self.data['current_namespaces_connections'] = sorted(namespaces_connections)

        if ns_tlog_gl.exception:
            raise ns_tlog_gl.exception
        tlog_connection = ns_tlog_gl.value

        if vm_gl.exception:
            raise vm_gl.exception
        vm_robot, ip = vm_gl.value

        self.logger.info("create the minio service on the vm")
        minio_data = {
            'zerodbs': namespaces_connections,
            'namespace': self.guid,
            'nsSecret': self.data['nsPassword'],
            'login': self.data['minioLogin'],
            'password': self.data['minioPassword'],
            'dataShard': self.data['dataShards'],
            'parityShard': self.data['parityShards'],
            'tlog': {
                'namespace': self.guid + '_tlog',
                'address': tlog_connection,
            },
            'blockSize': self.data['minioBlockSize'],
        }

        self.logger.info("wait up to 20 mins for zerorobot until it downloads the repos and starts accepting requests")
        now = time.time()
        minio = None
        while time.time() < now + 2400:
            try:
                minio = vm_robot.services.find_or_create(MINIO_TEMPLATE_UID, self.guid, minio_data)
                break
            except requests.ConnectionError:
                self.logger.info("vm not up yet...waiting some more")
                time.sleep(10)

        if not minio:
            raise RuntimeError('Failed to create minio service')

        self.logger.info("install minio")
        minio.schedule_action('install').wait(die=True)
        minio.schedule_action('start').wait(die=True)
        self.logger.info("minio installed")

        port = minio.schedule_action('node_port').wait(die=True).result

        self.logger.info("open port %s on minio vm", port)
        self._vm().schedule_action('add_portforward', args={'name': 'minio', 'target': port, 'source': None}).wait(die=True)

        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        # uninstall and delete all the created namespaces
        def delete_namespace(namespace):
            self.logger.info("deleting namespace %s on node %s", namespace['node'], namespace['url'])
            robot = get_zrobot(namespace['node'], namespace['url'])
            try:
                ns = robot.services.get(template_uid=NS_TEMPLATE_UID, name=namespace['name'])
                ns.schedule_action('uninstall').wait(die=True)
                ns.delete()
            except ServiceNotFoundError:
                pass

            if namespace in self.data['namespaces']:
                self.data['namespaces'].remove(namespace)

        group = gevent.pool.Group()
        namespaces = list(self.data['namespaces'])
        if self.data['tlog']:
            namespaces.append(self.data['tlog'])
        group.imap_unordered(delete_namespace, namespaces)
        group.join()
        self.data['tlog'] = None
        self.data['current_namespaces_connections'] = None

        try:
            # uninstall and delete the minio vm
            self.logger.info("deleting minio vm")
            vm = self._vm()
            vm.schedule_action('uninstall').wait(die=True)
            vm.delete()
        except ServiceNotFoundError:
            pass

        self.state.delete('actions', 'install')
        self.state.delete('status', 'running')

    def url(self):
        if not self.data['minioUrls']['public'] or not self.data['minioUrls']['storage']:
            self._update_url()
        return self.data['minioUrls']

    def start(self):
        self.state.check('actions', 'install', 'ok')
        vm_robot, _ = self._vm_robot_and_ip()
        minio = vm_robot.services.get(template_uid=MINIO_TEMPLATE_UID, name=self.guid)
        minio.schedule_action('start').wait(die=True)

    def stop(self):
        self.state.check('actions', 'install', 'ok')
        vm_robot, _ = self._vm_robot_and_ip()
        minio = vm_robot.services.get(template_uid=MINIO_TEMPLATE_UID, name=self.guid)
        minio.schedule_action('stop').wait(die=True)

    def upgrade(self):
        self.stop()
        self.start()

    def _vm(self):
        return self.api.services.get(template_uid=VM_TEMPLATE_UID, name=self.guid)

    def _vm_robot_and_ip(self):
        vm = self._vm()
        vminfo = vm.schedule_action('info', args={'timeout': 1200}).wait(die=True).result
        mgmt_ip = vminfo['zerotier'].get('ip')

        if not mgmt_ip:
            raise RuntimeError('VM has no ip assignments in zerotier network')
        ip = mgmt_ip

        return get_zrobot(vminfo['node_id'], 'http://{}:6600'.format(mgmt_ip)), ip

    def _deploy_minio_backend_namespaces(self):
        self.logger.info("create namespaces to be used as a backend for minio")

        self.logger.info("compute how much zerodb are required")
        required_nr_namespaces, namespace_size = compute_minimum_namespaces(total_size=self.data['storageSize'],
                                                                            data=self.data['dataShards'],
                                                                            parity=self.data['parityShards'])
        deployed_namespaces = []

        # Check if namespaces have already been created in a previous install attempt
        if self.data['namespaces']:
            for namespace in self.data['namespaces']:
                robot = get_zrobot(namespace['node'], namespace['url'])
                namespace = robot.services.get(template_uid=NS_TEMPLATE_UID, name=namespace['name'])
                deployed_namespaces.append(namespace)

        self.logger.info("namespaces required: %d of %dGB", required_nr_namespaces, namespace_size)
        self.logger.info("namespaces already deployed %d", len(deployed_namespaces))
        required_nr_namespaces = required_nr_namespaces - len(deployed_namespaces)
        for namespace, node in deploy_namespaces(nr_namepaces=required_nr_namespaces,
                                                 name=self.guid,
                                                 size=namespace_size,
                                                 storage_type=self.data['storageType'],
                                                 password=self.data['nsPassword'],
                                                 nodes=self._nodes,
                                                 logger=self.logger):
            deployed_namespaces.append(namespace)
            self.data['namespaces'].append({'name': namespace.name,
                                            'url': node['robot_address'],
                                            'node': node['node_id']})

            deployed_nr_namespaces = len(deployed_namespaces)
            self.logger.info("%d namespaces deployed, remaining %s", deployed_nr_namespaces, required_nr_namespaces - deployed_nr_namespaces)
            self.save()  # to save the already deployed namespaces

        if len(deployed_namespaces) < required_nr_namespaces:
            raise RuntimeError("could not deploy enough namespaces for minio data backend")

        return deployed_namespaces

    def _deploy_minio_tlog_namespace(self):
        self.logger.info("create namespaces to be used as a tlog for minio")

        # Check if namespaces have already been created in a previous install attempt
        if self.data.get('tlog') and self.data['tlog']['node'] and self.data['tlog']['url']:
            robot = get_zrobot(self.data['tlog']['node'], self.data['tlog']['url'])
            namespace = robot.services.get(template_uid=NS_TEMPLATE_UID, name=self.data['tlog']['name'])
            namespace.schedule_action('install').wait(die=True)
            return namespace

        tlog_namespace = None
        for namespace, node in deploy_namespaces(nr_namepaces=1,
                                                 name=self.guid + '_tlog',
                                                 size=10,  # TODO: compute how much is needed
                                                 storage_type='ssd',
                                                 password=self.data['nsPassword'],
                                                 nodes=self._nodes,
                                                 logger=self.logger):
            tlog_namespace = namespace
            self.data['tlog'] = {'name': tlog_namespace.name,
                                 'url': node['robot_address'],
                                 'node': node['node_id']}

        if not tlog_namespace:
            raise RuntimeError("could not deploy tlog namespace for minio")

        self.logger.info("tlog namespaces deployed")
        self.save()  # to save the already deployed namespaces

        return tlog_namespace

    def _deploy_minio_vm(self):
        self.logger.info("create the zero-os vm on which we will create the minio container")
        nodes = self._nodes.copy()

        nodes = sort_by_less_used(filter_node_online(nodes), 'sru')
        mgmt_nic = {
            'id': self.data['mgmtNic']['id'],
            'ztClient': self.data['mgmtNic']['ztClient'],
            'type': 'zerotier',
        }
        vm_data = {
            'cpu': 2,
            'memory': 4000,
            'image': 'zero-os',
            'mgmtNic': mgmt_nic,
            'disks': [{
                'diskType': 'ssd',
                'size': 10,  # FIXME: need to compute how much storage is needed on the disk to supprot X number of files in minio
                'label': 's3vm'
            }],
        }

        for node in nodes:
            vm_data['nodeId'] = node['node_id']
            vm = self.api.services.find_or_create(VM_TEMPLATE_UID, self.guid, vm_data)
            try:
                vm.state.check('actions', 'install', 'ok')
                return vm
            except StateCheckError:
                pass

            t = vm.schedule_action('install')
            t.wait()
            if t.state != 'ok':
                vm.delete(wait=True, timeout=60, die=False)

        return vm


def deploy_namespaces(nr_namepaces, name,  size, storage_type, password, nodes, logger):
    """
    generic function to deploy a group namespaces

    This function will yield namespaces as they are created
    It can return once nr_namespaces has been created or if we cannot create namespaces on any nodes.
    It is up to the caller to count the number of namespaces received from this function to know if the deployed enough namespaces
    """

    if storage_type not in ['ssd', 'hdd']:
        raise ValueError("storage_type must be 'ssd' or 'hdd', not %s" % storage_type)

    storage_key = 'sru' if storage_type == 'ssd' else 'hru'

    required_nr_namespaces = nr_namepaces
    deployed_nr_namespaces = 0
    nodes = filter_node_online(nodes.copy())
    while deployed_nr_namespaces < required_nr_namespaces:
        # sort nodes by the amount of storage available
        nodes = sort_by_less_used(nodes, storage_key)
        logger.info('number of possible nodes to use for namespace deployments %s', len(nodes))

        gls = set()
        for i in range(required_nr_namespaces - deployed_nr_namespaces):
            node = nodes[i % len(nodes)]
            logger.info("try to install namespace %s on node %s", name, node['node_id'])
            gls.add(gevent.spawn(install_namespace,
                                 node=node,
                                 name=name,
                                 disk_type=storage_type,
                                 size=size,
                                 password=password))

        for g in gevent.iwait(gls):
            if g.exception and g.exception.node in nodes:
                logger.error("we could not deploy on node %s, remove it from the possible node to use", node['node_id'])
                nodes.remove(g.exception.node)
            else:
                namespace, node = g.value
                deployed_nr_namespaces += 1

                # update amount of ressource so the next iteration of the loop will sort the list of nodes properly
                nodes[nodes.index(node)]['used_resources'][storage_key] += size

                yield (namespace, node)

        if len(nodes) <= 0:
            return


def list_farm_nodes(farm_organization):
    """
    return all the nodes detail from a farm

    :param farm_organization: IYO organization of the farm
    :type farm_organization: str
    :return: array container the detail of the nodes
    :rtype: array
    """
    capacity = j.clients.threefold_directory.get(interactive=False)
    resp = capacity.api.ListCapacity(query_params={'farmer': farm_organization})[1]
    resp.raise_for_status()
    return resp.json()


def install_namespace(node, name, disk_type, size, password):
    try:
        robot = get_zrobot(node['node_id'], node['robot_address'])
        data = {
            'diskType': disk_type,
            'mode': 'direct',
            'password': password,
            'public': False,
            'size': size,
            'nsName': name,
        }
        namespace = robot.services.create(template_uid=NS_TEMPLATE_UID, data=data)
        task = namespace.schedule_action('install').wait(timeout=300)
        if task.eco:
            namespace.delete()
            raise NamespaceDeployError(task.eco.message, node)
        return namespace, node

    except Exception as err:
        raise NamespaceDeployError(str(err), node)


def compute_minimum_namespaces(total_size, data, parity):
    """
    compute the number and size of zerodb namespace required to
    fulfill the erasure coding policy

    :param total_size: total size of the s3 storage
    :type total_size: int
    :param data: data shards number
    :type data: int
    :param parity: parity shard number
    :type parity: int
    :return: tuple with (number,size) of zerodb namespace required
    :rtype: tuple
    """
    max_shard_size = 1000  # 1TB

    # compute the require size to be able to store all the data+parity
    required_size = math.ceil((total_size * (data+parity)) / data)

    # take the minimum nubmer of shard and add a 25% to it
    nr_shards = math.ceil((data+parity) * 1.25)

    # compute the size of the shards
    shard_size = math.ceil(required_size / (data+parity))
    # if shard size is bigger then max, we limite the shard size
    # and increase the number of shards
    if shard_size > max_shard_size:
        shard_size = max_shard_size
        nr_shards = math.ceil(required_size / shard_size)

    return nr_shards, shard_size


def namespaces_connection_info(namespaces):
    group = gevent.pool.Group()
    return list(group.imap_unordered(namespace_connection_info, namespaces))


def namespace_connection_info(namespace):
    result = namespace.schedule_action('connection_info').wait(die=True).result
    # if there is not special storage network configured,
    # then the sal return the zerotier as storage address
    return '{}:{}'.format(result['storage_ip'], result['port'])


def get_zrobot(name, url):
    j.clients.zrobot.get(name, data={'url': url})
    return j.clients.zrobot.robots[name]


def sort_by_less_used(nodes, storage_key):
    def key(node):
        return node['total_resources'][storage_key] - node['used_resources'][storage_key]
    return sorted(nodes, key=key, reverse=True)


def filter_node_online(nodes):
    def url_ping(node):
        try:
            j.sal.nettools.checkUrlReachable(node['robot_address'], timeout=5)
            return (node, True)
        except:
            return (node, False)

    group = gevent.pool.Group()
    for node, ok in group.imap_unordered(url_ping, nodes):
        if ok:
            yield node


class NamespaceDeployError(RuntimeError):
    def __init__(self, msg, node):
        super().__init__(self, msg)
        self.node = node
