import json
import math
import time
import requests

from js9 import j

from zerorobot.template.base import TemplateBase

VM_TEMPLATE_UID = 'github.com/jumpscale/digital_me/vm/0.0.1'
MINIO_TEMPLATE_UID = 'github.com/zero-os/0-templates/minio/0.0.1'
NS_TEMPLATE_UID = 'github.com/zero-os/0-templates/namespace/0.0.1'


class S3(TemplateBase):
    version = '0.0.1'
    template_name = "s3"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self._nodes = []

    def _get_zrobot(self, name, url):
        j.clients.zrobot.get(name, data={'url': url})
        return j.clients.zrobot.robots[name]

    def validate(self):
        if self.data['parityShards'] > self.data['dataShards']:
            raise ValueError('parityShards must be equal to or less than dataShards')

        capacity = j.clients.grid_capacity.get(interactive=False)
        resp = capacity.api.ListCapacity(query_params={'farmer': self.data['farmerIyoOrg']})[1]
        resp.raise_for_status()
        self._nodes = resp.json()

        if not self._nodes:
            raise ValueError('There are no nodes in this farm')

    def _create_namespace(self, index, storage_key, password):
        final_index = index
        while True:
            next_index = final_index + 1 if final_index < len(self._nodes) - 2 else 0
            # if the current node candidate has enough storage, try to create a namespace on it
            if self._nodes[final_index][storage_key] >= self.data['storageSize']:
                best_node = self._nodes[final_index]
                robot = self._get_zrobot(best_node['node_id'], best_node['robot_address'])
                data = {
                    'disktype': self.data['storageType'],
                    'mode': 'user',
                    'password': password,
                    'public': True,
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
                    best_node[storage_key] = best_node[storage_key] - self.data['storageSize']
                    self.data['namespaces'].append({'name': namespace.name, 'url': best_node['robot_address'], 'node': best_node['node_id']})
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
        self._nodes = sorted(self._nodes, key=lambda k: k[storage_key], reverse=True)

        # Create namespaces to be used as a backend for minio
        node_index = 0
        for i in range(zdb_count):
            namespace, node_index = self._create_namespace(node_index, storage_key, ns_password)
            result = namespace.schedule_action('connection_info').wait(die=True).result
            zdbs_connection.append('{}:{}'.format(result['ip'], result['port']))

        self._nodes = sorted(self._nodes, key=lambda k: k[storage_key], reverse=True)

        # Create the zero-os vm on which we will create the minio container
        vm_data = {
            'memory': 2000,
            'image': 'zero-os',
            'zerotier': {
                'id': self.data['vmZerotier']['id'],
                'ztClient': self.data['vmZerotier']['ztClient'],
            },
            'disks': [{
                'diskType': 'hdd',
                'size': 5,
                'mountPoint': '/mnt',
                'filesystem': 'btrfs',
                'label': 's3vm'
            }],
            'nodeId': self._nodes[0]['node_id'],
        }

        vm = self.api.services.create(VM_TEMPLATE_UID, self.guid, vm_data)
        vm.schedule_action('install').wait(die=True)
        vminfo = vm.schedule_action('info', args={'timeout': 600}).wait(die=True).result
        ip = vminfo['zerotier'].get('ip')

        if not ip:
            raise RuntimeError('VM has no ip assignments in zerotier network')

        vm_robot = self._get_zrobot(vm.name, 'http://{}:6600'.format(ip))

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
        while time.time() < now + 1200:
            try:
                minio = vm_robot.services.find_or_create(MINIO_TEMPLATE_UID, self.guid, minio_data)
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
            # robot = self._get_zrobot('main', 'http://localhost:6600')
            ns = robot.services.get(template_uid=NS_TEMPLATE_UID, name=namespace['name'])
            ns.schedule_action('uninstall').wait(die=True)
            ns.delete()
            self.data['namespaces'].remove(namespace)

        # uninstall and delete the minio vm
        vm = self.api.services.get(template_uid=VM_TEMPLATE_UID, name=self.guid)
        vm.schedule_action('uninstall').wait(die=True)
        vm.delete()

    def url(self):
        return self.data['minioUrl']
