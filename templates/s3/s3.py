import json
import math
import time
import requests

from jumpscale import j

from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError
from zerorobot.template.decorator import timeout


VM_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/dm_vm/0.0.1'
MINIO_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/minio/0.0.1'
NS_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/namespace/0.0.1'


class S3(TemplateBase):
    version = '0.0.1'
    template_name = "s3"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.recurring_action('_monitor', 30)  # every 30 seconds
        self._nodes = []

    def _monitor(self):
        self.logger.info('Monitor s3 %s' % self.name)
        self.state.check('actions', 'install', 'ok')

        @timeout(10)
        def update_state():
            vm_robot, _ = self._vm_robot_and_ip()
            state = vm_robot.services.get(template_uid=MINIO_TEMPLATE_UID, name=self.guid).state
            try:
                state.check('status', 'running', 'ok')
                self.state.set('status', 'running', 'ok')
                return
            except StateCheckError:
                self.state.delete('status', 'running')
                zdbs_connection = []
                for namespace in self.data['namespaces']:
                    robot = self._get_zrobot(namespace['node'], namespace['url'])
                    ns = robot.services.get(template_uid=NS_TEMPLATE_UID, name=namespace['name'])
                    try:
                        ns.state.check('status', 'running', 'ok')
                        result = ns.schedule_action('connection_info').wait(die=True).result
                        zdbs_connection.append('{}:{}'.format(result['ip'], result['port']))
                    except StateCheckError:
                        break
                else:
                    minio = vm_robot.services.get(template_uid=MINIO_TEMPLATE_UID, name=self.guid)
                    minio.schedule_action('update_zerodbs', args={'zerodbs': zdbs_connection}).wait(die=True)
                    minio.state.set('zerodbs', 'started', 'ok')

        try:
            update_state()
        except:
            self.state.delete('status', 'running')

    def _get_zrobot(self, name, url):
        j.clients.zrobot.get(name, data={'url': url})
	# j.clients.zrobot.get(name, data={'url': 'http://172.30.115.224:6600'})
        return j.clients.zrobot.robots[name]

    def _vm(self):
        return self.api.services.get(template_uid=VM_TEMPLATE_UID, name=self.guid)

    def _vm_robot_and_ip(self):
        vm = self._vm()
        vminfo = vm.schedule_action('info', args={'timeout': 600}).wait(die=True).result
        # @todo: handle ip in case of vxlan
        ip = vminfo['zerotier'].get('ip')

        if not ip:
            raise RuntimeError('VM has no ip assignments in zerotier network')

        return self._get_zrobot(vm.name, 'http://{}:6600'.format(ip)), ip

    def validate(self):
        if self.data['parityShards'] > self.data['dataShards']:
            raise ValueError('parityShards must be equal to or less than dataShards')

        capacity = j.clients.grid_capacity.get(interactive=False)
        resp = capacity.api.ListCapacity(query_params={'farmer': self.data['farmerIyoOrg']})[1]
        resp.raise_for_status()
        self._nodes = resp.json()
        # resp = resp.json()
        # for i in range(0, len(resp)):
        #     if resp[i]['node_id'] == 'ac1f6b457bd8':
        #         self._nodes = [resp[i]]

        if not self._nodes:
            raise ValueError('There are no nodes in this farm')

    def _create_namespace(self, index, storage_key, password):
        final_index = index
        while True:
            next_index = final_index + 1 if final_index < len(self._nodes) - 2 else 0
            # if the current node candidate has enough storage, try to create a namespace on it
            if self._nodes[final_index]['total_resources'][storage_key] >= self.data['storageSize']:
                best_node = self._nodes[final_index]
                robot = self._get_zrobot(best_node['node_id'], best_node['robot_address'])
                data = {
                    'diskType': self.data['storageType'],
                    'mode': 'direct',
                    'password': password,
                    'public': False,
                    'size': self.data['storageSize'],
                    'nsName': self.guid,
                }
                namespace = robot.services.create(
                    service_name=j.data.idgenerator.generateXCharID(16),
                    template_uid=NS_TEMPLATE_UID, data=data)

                task = namespace.schedule_action('install').wait()
                if task.eco:
                    if task.eco.exceptionclassname == 'NoNamespaceAvailability':
                        namespace.delete()
                    else:
                        raise RuntimeError(task.eco.errormessage)
                else:
                    best_node['total_resources'][storage_key] = best_node['total_resources'][storage_key] - self.data['storageSize']
                    self.data['namespaces'].append(
                        {'name': namespace.name, 'url': best_node['robot_address'], 'node': best_node['node_id']})
                    return namespace, next_index

            if next_index == index:
                raise RuntimeError('Looped all nodes and could not find a suitable node')
            final_index = next_index

    def install(self):

        # Calculate how many zerodbs are needed for the s3
        # based on this https://godoc.org/github.com/zero-os/0-stor/client/datastor/pipeline#ObjectDistributionConfig
        # I compute the max and min and settle half way between them
        # @todo this probably needs to changed at some point
        zdb_count = 1
        if self.data['dataShards'] and not self.data['parityShards']:
            zdb_count = self.data['dataShards']
        else:
            max_zdb = self.data['dataShards'] + self.data['parityShards']
            min_zdb = self.data['dataShards'] - self.data['parityShards']
            zdb_count = math.ceil(min_zdb + ((max_zdb - min_zdb)/2))

        storage_key = 'sru' if self.data['storageType'] == 'ssd' else 'hru'
        ns_password = j.data.idgenerator.generateXCharID(32)
        zdbs_connection = list()
        self._nodes = sorted(self._nodes, key=lambda k: k['total_resources'][storage_key], reverse=True)

        # Create namespaces to be used as a backend for minio
        node_index = 0
        for _ in range(zdb_count):
            namespace, node_index = self._create_namespace(node_index, storage_key, ns_password)
            result = namespace.schedule_action('connection_info').wait(die=True).result
            if self.data['nic']['type'] == 'zerotier':
                zdbs_connection.append('{}:{}'.format(result['storage_ip'], result['port']))
                continue
            zdbs_connection.append('{}:{}'.format(result['ip'], result['port']))

        self._nodes = sorted(self._nodes, key=lambda k: k['total_resources'][storage_key], reverse=True)

        # Create the zero-os vm on which we will create the minio container
        vm_data = {
            'memory': 2000,
            'image': 'zero-os',
            'nic': {
                'id': self.data['vmNic']['id'],
                'ztClient': self.data['vmNic']['ztClient'],
                'type': self.data['vmNic']['type'],
            },
            'disks': [{
                'diskType': self.data['storageType'],
                'size': 5,
                'mountPoint': '/mnt',
                'filesystem': 'btrfs',
                'label': 's3vm'
            }],
            'nodeId': self._nodes[0]['node_id'],
        }

        vm = self.api.services.create(VM_TEMPLATE_UID, self.guid, vm_data)
        vm.schedule_action('install').wait(die=True)
        vm_robot, ip = self._vm_robot_and_ip()

        # Create the minio service on the vm
        minio_data = {
            'zerodbs': zdbs_connection,
            'namespace': self.guid,
            'nsSecret': ns_password,
            'login': self.data['minioLogin'],
            'password': self.data['minioPassword'],
        }

        # Wait 20 mins for zerorobot until it downloads the repos and starts accepting requests
        now = time.time()
        minio = None
        while time.time() < now + 2400:
            try:
                minio = vm_robot.services.find_or_create(MINIO_TEMPLATE_UID, self.guid, minio_data)
                minio.state.set('zerodbs', 'started', 'ok')
                break
            except requests.ConnectionError:
                time.sleep(10)

        if not minio:
            raise RuntimeError('Failed to create minio service')

        minio.schedule_action('install').wait(die=True)
        minio.schedule_action('start').wait(die=True)
        port = minio.schedule_action('node_port').wait(die=True).result
        self.data['minioUrl'] = 'http://{}:{}'.format(ip, port)

        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        # uninstall and delete all the created namespaces
        for namespace in self.data['namespaces']:
            robot = self._get_zrobot(namespace['node'], namespace['url'])
            ns = robot.services.get(template_uid=NS_TEMPLATE_UID, name=namespace['name'])
            ns.schedule_action('uninstall').wait(die=True)
            ns.delete()
            self.data['namespaces'].remove(namespace)

        # uninstall and delete the minio vm
        vm = self._vm()
        vm.schedule_action('uninstall').wait(die=True)
        vm.delete()

    def url(self):
        return self.data['minioUrl']

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
