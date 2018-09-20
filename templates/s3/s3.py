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
        self.recurring_action('_monitor', 30)  # every 30 seconds
        self._nodes = []

    def validate(self):
        if self.data['parityShards'] > self.data['dataShards']:
            raise ValueError('parityShards must be equal to or less than dataShards')

        if len(self.data['minioPassword']) < 8:
            raise ValueError("minio password need to be at least 8 characters")

        self._nodes = list_farm_nodes(self.data['farmerIyoOrg'])
        if not self._nodes:
            raise ValueError('There are no nodes in this farm')

        if not self.data['nsPassword']:
            self.data['nsPassword'] = j.data.idgenerator.generateXCharID(32)

    def _monitor(self):
        self.logger.info('Monitor s3 %s' % self.name)
        self.state.check('actions', 'install', 'ok')

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
        def deploy_namespaces():
            namespaces = self._deploy_namespaces()
            namespaces_connections = namespaces_connection_info(namespaces)
            return namespaces_connections

        def deploy_vm():
            self._deploy_minio_vm()
            return self._vm_robot_and_ip()

        # deploy all namespaces and vm concurrently
        ns_gl = gevent.spawn(deploy_namespaces)
        vm_gl = gevent.spawn(deploy_vm)
        gevent.wait([ns_gl, vm_gl])

        if ns_gl.exception:
            raise ns_gl.exception
        namespaces_connections = ns_gl.value

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
            'parityShard': self.data['parityShards']
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
            ns = robot.services.get(template_uid=NS_TEMPLATE_UID, name=namespace['name'])
            ns.schedule_action('uninstall').wait(die=True)
            ns.delete()
            self.data['namespaces'].remove(namespace)

        group = gevent.pool.Group()
        group.imap_unordered(delete_namespace, list(self.data['namespaces']))
        group.join()

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
        vm_robot, public_ip = self._vm_robot_and_ip()
        minio = vm_robot.services.get(template_uid=MINIO_TEMPLATE_UID, name=self.guid)
        public_port = minio.schedule_action('node_port').wait(die=True).result

        vm_info = self._vm().schedule_action('info').wait(die=True).result
        storage_ip = vm_info['host']['storage_addr']
        storage_port = None
        for src, dest in vm_info['ports'].items():
            if dest == public_port:
                storage_port = int(src)
                break

        output = {
            'public': 'http://{}:{}'.format(public_ip, public_port),
            'storage': '',
        }
        if storage_ip and storage_port:
            output['storage'] = 'http://{}:{}'.format(storage_ip, storage_port)

        return output

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

    def _gateway(self):
        robot = j.clients.zrobot.robots[self.data['gatewayRobot']]
        return robot.services.get(template_uid=GATEWAY_TEMPLATE_UID, name=self.data['gateway'])

    def _vm_robot_and_ip(self):
        vm = self._vm()
        vminfo = vm.schedule_action('info', args={'timeout': 1200}).wait(die=True).result
        mgmt_ip = vminfo['zerotier'].get('ip')

        if not mgmt_ip:
            raise RuntimeError('VM has no ip assignments in zerotier network')
        ip = mgmt_ip

        return get_zrobot(vm.name, 'http://{}:6600'.format(mgmt_ip)), ip

    def _deploy_namespaces(self):
        self.logger.info("create namespaces to be used as a backend for minio")

        self.logger.info("compute how much zerodb are required")
        required_nr_namespaces = compute_minumum_namespaces(total_size=self.data['storageSize'],
                                                            data=self.data['dataShards'],
                                                            parity=self.data['parityShards'],
                                                            shard_size=self.data['shardSize'])
        deployed_nr_namespaces = 0
        deployed_namespaces = []

        # Check if namespaces have already been created in a previous install attempt
        if self.data['namespaces']:
            for namespace in self.data['namespaces']:
                robot = get_zrobot(namespace['node'], namespace['url'])
                namespace = robot.services.get(template_uid=NS_TEMPLATE_UID, name=namespace['name'])
                deployed_namespaces.append(namespace)

        self.logger.info("namespaces required %d", required_nr_namespaces)
        self.logger.info("namespaces already deployed %d", len(deployed_namespaces))
        required_nr_namespaces = required_nr_namespaces - len(deployed_namespaces)

        storage_key = 'sru' if self.data['storageType'] == 'ssd' else 'hru'
        while deployed_nr_namespaces < required_nr_namespaces:
            # sort nodes by the amount of storage available
            nodes = sorted(self._nodes, key=lambda k: k['total_resources'][storage_key], reverse=True)

            gls = set()
            for i in range(required_nr_namespaces - deployed_nr_namespaces):
                node = nodes[i % len(nodes)]
                gls.add(gevent.spawn(install_namespace,
                                     node=node,
                                     name=self.guid,
                                     disk_type=self.data['storageType'],
                                     size=self.data['shardSize'],
                                     password=self.data['nsPassword']))

            for g in gevent.wait(gls):
                if g.exception:
                    if g.exception.node in nodes:
                        # we could not deploy on this node, remove it from the possible node to use
                        nodes.remove(g.exception.node)
                else:
                    namespace, node = g.value
                    deployed_namespaces.append(namespace)
                    self.data['namespaces'].append({'name': namespace.name,
                                                    'url': node['robot_address'],
                                                    'node': node['node_id']})
                    # update amount of ressource so the next iteration of the loop will sort the list of nodes properly
                    nodes[nodes.index(node)]['total_resources'][storage_key] -= self.data['shardSize']

            self.save()  # to save the already deployed namespaces
            deployed_nr_namespaces = len(deployed_namespaces)
            self.logger.info("%d namespaces deployed, remaining %s", deployed_nr_namespaces, required_nr_namespaces - deployed_nr_namespaces)
            if len(nodes) <= 0:
                raise RuntimeError('could not deploy enough namespaces')

        return deployed_namespaces

    def _deploy_minio_vm(self):
        self.logger.info("create the zero-os vm on which we will create the minio container")
        vm_node_id = pick_vm_node(self._nodes)
        if vm_node_id is None:
            raise RuntimeError("no node found to deploy vm on it")

        mgmt_nic = {
            'id': self.data['mgmtNic']['id'],
            'ztClient': self.data['mgmtNic']['ztClient'],
            'type': 'zerotier',
        }
        vm_data = {
            'memory': 2000,
            'image': 'zero-os',
            'mgmtNic': mgmt_nic,
            'disks': [{
                'diskType': 'ssd',
                'size': 10,  # FIXME: need to compute how much storage is needed on the disk to supprot X number of files in minio
                'label': 's3vm'
            }],
            'nodeId': vm_node_id,
        }

        vm = self.api.services.find_or_create(VM_TEMPLATE_UID, self.guid, vm_data)
        try:
            vm.state.check('actions', 'install', 'ok')
        except StateCheckError:
            vm.schedule_action('install').wait(die=True)

        return vm


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
        task = namespace.schedule_action('install').wait()
        if task.eco:
            if task.eco.category == 'python.NoNamespaceAvailability':
                namespace.delete()
            else:
                raise NamespaceDeployError(task.eco.message, node)
        return namespace, node

    except Exception as err:
        raise NamespaceDeployError(str(err), node)


def compute_minumum_namespaces(total_size, data, parity, shard_size=2000):
    """
    compute the minumum number of zerodb required to
    fulfill the erasure coding policy


    :param data: data shards number
    :type data: int
    :param parity: parity shard number
    :type parity: int
    :return: minumum number of zerodb required
    :rtype: int
    """
    return math.ceil(((total_size * (data+parity)) / data) / shard_size)


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


def pick_vm_node(nodes):
    """
    try to find a node where we can deploy the minio VM

    :param nodes: list of nodes from the farm
    :type nodes: list
    :return: the node id of the selected node
    :rtype: string
    """

    # sort all the node by the amount of storage available
    # TODO: better sorting logic taking in account memory and CPU available too
    nodes = sorted(nodes, key=lambda k: k['total_resources']['sru'], reverse=True)
    selected_node = None
    for node in nodes:
        robot = get_zrobot(node['node_id'], node['robot_address'])
        try:
            # make sure the robot is reachable
            robot.services.find()
            selected_node = node['node_id']
            break
        except:
            continue

    return selected_node


class NamespaceDeployError(RuntimeError):
    def __init__(self, msg, node):
        super().__init__(self, msg)
        self.node = node
