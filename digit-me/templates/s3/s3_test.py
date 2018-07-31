from unittest.mock import MagicMock, patch, PropertyMock
import os
import requests
import pytest

from js9 import j
from s3 import S3

from JumpScale9Zrobot.test.utils import ZrobotBaseTest


class TestS3Template(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), S3)

    def setUp(self):
        self.valid_data = {
            'vmZerotier': {
                'id': 'network_id',
                'ztClient': 'main'
            },
            'farmerIyoOrg': 'org',
            'dataShards': 1,
            'parityShars': 0,
            'storageType': 'ssd',
            'storageSize': 10,
            'namespaces': [],
            'minioLogin': 'login',
            'minioPassword': 'password',
            'minioUrl': 'url',
        }
        patch('js9.j.clients', MagicMock()).start()
        self.s3 = S3('s3', data=self.valid_data)

    def tearDown(self):
        patch.stopall()

    def test_get_zrobot(self):
        patch('js9.j.clients.zrobot', MagicMock(robots={'main': 'main'})).start()
        robot = self.s3._get_zrobot('main', 'url')
        assert j.clients.zrobot.get.called_once_with('main', data={'url': 'url'})
        assert robot == 'main'

    def test_invalid_data(self):
        with pytest.raises(ValueError, message='template should fail if parityShards are higher than dataShards'):
            data = dict(self.valid_data)
            data['parityShards'] = 5
            s3 = S3('s3', data=data)
            s3.validate()

        with pytest.raises(ValueError, message='template should fail if there are no nodes in the farmer org'):
            resp = MagicMock()
            resp.json.return_value = []
            patch('js9.j.clients.grid_capacity.get.return_value.api.ListCapacity.return_value', [0, resp]).start()
            self.s3.validate()

    def test_url(self):
        assert self.s3.url() == self.valid_data['minioUrl']

    def test_uninstall(self):
        self.valid_data['namespaces'] = [{'node': 'node', 'url': 'url', 'name': 'name'}]
        s3 = S3('s3', data=self.valid_data)
        robot = MagicMock()
        s3.api.services.get = MagicMock()
        s3._get_zrobot = robot
        s3.uninstall()
        robot.return_value.services.get.return_value.schedule_action.assert_called_once_with('uninstall')
        robot.return_value.services.get.return_value.delete.assert_called_once_with()
        assert s3.data['namespaces'] == []

        s3.api.services.get.return_value.schedule_action.assert_called_once_with('uninstall')
        s3.api.services.get.return_value.delete.assert_called_once_with()

    def test_create_namespace_no_suitable_nodes_with_enough_storage(self):
        with pytest.raises(RuntimeError, message='template should fail if there is no suitable node found'):
            self.s3._nodes = [{'sru': 5}]
            self.s3._create_namespace(0, 'sru', 'password')

    def test_create_namespace_no_suitable_nodes_with_available_namespace(self):
        with pytest.raises(RuntimeError, message='template should fail if there is no suitable node found'):
            self.s3._nodes = [{'sru': 20, 'node_id': 'node_id', 'robot_address': 'robot_address'}]
            self.s3._get_zrobot = MagicMock()
            namespace = self.s3._get_zrobot.return_value.services.create.return_value
            namespace.schedule_action.return_value.wait.return_value.eco = MagicMock(exceptionclassname='NoNamespaceAvailability')
            self.s3._create_namespace(0, 'sru', 'password')
            namespace.delete.assert_called_once_with()

    def test_create_namespace_install_error(self):
        with pytest.raises(RuntimeError, message='template should fail if there is no suitable node found'):
            self.s3._nodes = [{'sru': 20, 'node_id': 'node_id', 'robot_address': 'robot_address'}]
            self.s3._get_zrobot = MagicMock()
            self.s3._create_namespace(0, 'sru', 'password')
            self.s3._get_zrobot.return_value.services.create.return_value.delete.assert_not_called()

    def test_create_namespace(self):
        self.s3._nodes = [{'sru': 20, 'node_id': 'node_id', 'robot_address': 'robot_address'}]
        self.s3._get_zrobot = MagicMock()
        namespace = self.s3._get_zrobot.return_value.services.create.return_value
        namespace.schedule_action.return_value.wait.return_value.eco = None
        namespace.name = 'name'
        ns, index = self.s3._create_namespace(0, 'sru', 'password')
        assert ns == namespace
        assert index == 0
        assert self.s3._nodes[0]['sru'] == 10
        assert self.s3.data['namespaces'] == [{'name': 'name', 'url': 'robot_address', 'node': 'node_id'}]

    def test_install_failed_to_find_vm(self):
        with pytest.raises(RuntimeError, message='template should fail if it fails to find vm in zt network'):
            self.s3._nodes = [{'sru': 20, 'node_id': 'node_id', 'robot_address': 'robot_address'}]
            self.s3._create_namespace = MagicMock()
            namespace = MagicMock()
            namespace.schedule_action.return_value.wait.return_value.result = {'ip': '127.0.0.01', 'port': 9000}
            self.s3._create_namespace.return_value = (namespace, 0)
            vm = MagicMock()
            vm.schedule_action.return_value.wait.return_value.result = {'zerotier': {}}
            self.s3.api.services.create = MagicMock(return_value=vm)

            self.s3.install()

    def test_install_no_ip_assignments(self):
        with pytest.raises(RuntimeError, message='template should fail if vm has no ip assignments'):
            self.s3._nodes = [{'sru': 20, 'node_id': 'node_id', 'robot_address': 'robot_address'}]
            self.s3._create_namespace = MagicMock()
            namespace = MagicMock()
            namespace.schedule_action.return_value.wait.return_value.result = {'ip': '127.0.0.01', 'port': 9000}
            self.s3._create_namespace.return_value = (namespace, 0)
            vm = MagicMock()
            vm.schedule_action.return_value.wait.return_value.result = {'zerotier': {'ip': ''}}
            self.s3.api.services.create = MagicMock(return_value=vm)
            patch('time.time', MagicMock(side_effect=[1, 2, 3, 700])).start()
            self.s3.install()

    def test_install_minio_fails(self):
        with pytest.raises(RuntimeError, message='template should fail if it fails to create minio service'):
            self.s3._nodes = [{'sru': 20, 'node_id': 'node_id', 'robot_address': 'robot_address'}]
            self.s3._create_namespace = MagicMock()
            namespace = MagicMock()
            namespace.schedule_action.return_value.wait.return_value.result = {'ip': '127.0.0.01', 'port': 9000}
            self.s3._create_namespace.return_value = (namespace, 0)
            vm = MagicMock()
            vm.schedule_action.return_value.wait.return_value.result = {'zerotier': {'ip': '127.0.0.1'}}
            self.s3.api.services.create = MagicMock(return_value=vm)
            patch('time.time', MagicMock(side_effect=[1, 2, 1, 2, 1300])).start()
            patch('time.sleep', MagicMock()).start()
            vm_robot = MagicMock()
            vm_robot.services.find_or_create.side_effect = requests.ConnectionError
            self.s3._get_zrobot = MagicMock(return_value=vm_robot)
            self.s3.install()

    def test_install_success(self):
        self.s3._nodes = [{'sru': 20, 'node_id': 'node_id', 'robot_address': 'robot_address'}]
        self.s3._create_namespace = MagicMock()
        namespace = MagicMock()
        namespace.schedule_action.return_value.wait.return_value.result = {'ip': '127.0.0.01', 'port': 9000}
        self.s3._create_namespace.return_value = (namespace, 0)
        vm = MagicMock()
        vm.schedule_action.return_value.wait.return_value.result = {'zerotier': {'ip': 'ip'}}
        self.s3.api.services.create = MagicMock(return_value=vm)
        minio = MagicMock()
        minio.schedule_action.return_value.wait.return_value.result = 9001
        vm_robot = MagicMock()
        vm_robot.services.find_or_create.return_value = minio
        self.s3._get_zrobot = MagicMock(return_value=vm_robot)
        self.s3.install()
        assert self.s3.data['minioUrl'] == 'http://ip:9001'
