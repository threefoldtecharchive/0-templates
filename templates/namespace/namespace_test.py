from unittest.mock import MagicMock
import os
import pytest

from namespace import Namespace
from zerorobot.template.state import StateCheckError
from zerorobot.service_collection import ServiceNotFoundError

from JumpscaleZrobot.test.utils import ZrobotBaseTest, task_mock


class TestNamespaceTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), Namespace)
        cls.valid_data = {
            'diskType': 'HDD',
            'mode': 'user',
            'password': 'mypasswd',
            'public': False,
            'size': 20,
            'nsName': '',
        }

    def test_invalid_data(self):
        with pytest.raises(ValueError, message='template should fail to instantiate if data dict is missing the size'):
            data = self.valid_data.copy()
            data.pop('size')
            ns = Namespace(name='namespace', data=data)
            ns.api.services.get = MagicMock()
            ns.validate()

    def test_no_node_installed(self):
        with pytest.raises(RuntimeError, message='template should fail to install if no service node is installed'):
            ns = Namespace(name='namespace', data=self.valid_data)
            ns.api.services.get = MagicMock(side_effect=ServiceNotFoundError)
            ns.validate()

        with pytest.raises(RuntimeError, message='template should fail to install if no service node is installed'):
            ns = Namespace(name='namespace', data=self.valid_data)
            node = MagicMock()
            node.state.check = MagicMock(side_effect=StateCheckError)
            ns.api.services.get = MagicMock(return_value=node)
            ns.validate()

    def test_valid_data(self):
        ns = Namespace(name='namespace', data=self.valid_data)
        ns.api.services.get = MagicMock()
        ns.validate()
        data = self.valid_data.copy()
        data['zerodb'] = ''
        data['nsName'] = ''
        assert ns.data == data

    def test_zerodb_property(self):
        ns = Namespace(name='namespace', data=self.valid_data)
        ns.api.services.get = MagicMock(return_value='zerodb')
        assert ns._zerodb == 'zerodb'

    def test_install(self):
        ns = Namespace(name='namespace', data=self.valid_data)
        node = MagicMock()
        node.schedule_action = MagicMock(return_value=task_mock(('instance', 'nsName')))
        ns.api = MagicMock()
        ns.api.services.get = MagicMock(return_value=node)
        args = {
            'disktype': ns.data['diskType'].upper(),
            'mode': ns.data['mode'],
            'password': ns.data['password'],
            'public': ns.data['public'],
            'size': ns.data['size'],
            'name': ns.data['nsName']
        }
        ns.install()

        node.schedule_action.assert_called_once_with('create_zdb_namespace', args)
        ns.state.check('actions', 'install', 'ok')
        assert ns.data['nsName'] == 'nsName'
        assert ns.data['zerodb'] == 'instance'

    def test_info_without_install(self):
        with pytest.raises(StateCheckError, message='Executing info action without install should raise an error'):
            ns = Namespace(name='namespace', data=self.valid_data)
            ns.info()

    def test_info(self):
        ns = Namespace(name='namespace', data=self.valid_data)
        ns.data['nsName'] = 'nsName'
        ns.state.set('actions', 'install', 'ok')
        ns.api = MagicMock()
        task = task_mock('info')
        ns._zerodb.schedule_action = MagicMock(return_value=task)

        assert ns.info() == 'info'
        ns._zerodb.schedule_action.assert_called_once_with('namespace_info', args={'name': ns.data['nsName']})

    def test_uninstall_without_install(self):
        with pytest.raises(StateCheckError, message='Executing uninstall action without install should raise an error'):
            ns = Namespace(name='namespace', data=self.valid_data)
            ns.uninstall()

    def test_uninstall(self):
        ns = Namespace(name='namespace', data=self.valid_data)
        ns.data['nsName'] = 'nsName'
        ns.state.set('actions', 'install', 'ok')
        ns.api = MagicMock()
        ns.uninstall()
        ns._zerodb.schedule_action.assert_called_once_with('namespace_delete', args={'name': 'nsName'})

    def test_connection_info_without_install(self):
        with pytest.raises(StateCheckError, message='Executing connection_info action without install should raise an error'):
            ns = Namespace(name='namespace', data=self.valid_data)
            ns.connection_info()

    def test_connection_info(self):
        ns = Namespace(name='namespace', data=self.valid_data)
        ns.state.set('actions', 'install', 'ok')
        ns.state.set('status', 'running', 'ok')
        ns.api = MagicMock()
        result = {'ip': '127.0.0.1', 'port': 9900}
        task = task_mock(result)
        ns._zerodb.schedule_action = MagicMock(return_value=task)
        assert ns.connection_info() == result
        ns._zerodb.schedule_action.assert_called_once_with('connection_info')

    def test_url_without_install(self):
        with pytest.raises(StateCheckError, message='Executing info action without install should raise an error'):
            ns = Namespace(name='namespace', data=self.valid_data)
            ns.url()

    def test_url(self):
        ns = Namespace(name='namespace', data=self.valid_data)
        ns.data['nsName'] = 'nsName'
        ns.state.set('actions', 'install', 'ok')
        ns.api = MagicMock()
        ns._zerodb.schedule_action = MagicMock(return_value=task_mock('url'))

        assert ns.url() == 'url'
        ns._zerodb.schedule_action.assert_called_once_with('namespace_url', args={'name': 'nsName'})

    def test_private_url_without_install(self):
        with pytest.raises(StateCheckError, message='Executing info action without install should raise an error'):
            ns = Namespace(name='namespace', data=self.valid_data)
            ns.url()

    def test_private_url(self):
        ns = Namespace(name='namespace', data=self.valid_data)
        ns.data['nsName'] = 'nsName'
        ns.state.set('actions', 'install', 'ok')
        ns.api = MagicMock()
        ns._zerodb.schedule_action = MagicMock(return_value=task_mock('url'))

        assert ns.private_url() == 'url'
        ns._zerodb.schedule_action.assert_called_once_with('namespace_private_url', args={'name': 'nsName'})
