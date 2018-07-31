from unittest.mock import MagicMock, patch
import os
import pytest

from vdisk import Vdisk
from zerorobot.template.state import StateCheckError
from zerorobot.service_collection import ServiceNotFoundError

from JumpScale9Zrobot.test.utils import ZrobotBaseTest, task_mock


class TestVdiskTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), Vdisk)
        cls.valid_data = {
            'diskType': 'HDD',
            'size': 20,
            'mountPoint': '',
            'filesystem': '',
            'mode': 'user',
            'public': False,
            'label': 'label',
        }

    def setUp(self):
        patch('js9.j.clients.zos.sal', MagicMock()).start()

    def tearDown(self):
        patch.stopall()

    def test_invalid_data(self):
        with pytest.raises(ValueError, message='template should fail to instantiate if data dict is missing the diskType'):
            vdisk = Vdisk(name='vdisk', data={})
            vdisk.api.services.get = MagicMock()
            vdisk.validate()

        with pytest.raises(ValueError, message='template should fail to instantiate if data dict is missing the size'):
            vdisk = Vdisk(name='vdisk', data={'diskType': 'hdd'})
            vdisk.api.services.get = MagicMock()
            vdisk.validate()

        with pytest.raises(ValueError, message='template should fail to instantiate if data dict is missing the label'):
            vdisk = Vdisk(name='vdisk', data={'diskType': 'hdd', 'size': 5})
            vdisk.api.services.get = MagicMock()
            vdisk.validate()

    def test_no_node_installed(self):
        with pytest.raises(RuntimeError, message='template should fail to install if no service node is installed'):
            vdisk = Vdisk(name='vdisk', data=self.valid_data)
            vdisk.api.services.get = MagicMock(side_effect=ServiceNotFoundError)
            vdisk.validate()

        with pytest.raises(RuntimeError, message='template should fail to install if no service node is installed'):
            vdisk = Vdisk(name='vdisk', data=self.valid_data)
            node = MagicMock()
            node.state.check = MagicMock(side_effect=StateCheckError)
            vdisk.api.services.get = MagicMock(return_value=node)
            vdisk.validate()

    def test_valid_data(self):
        vdisk = Vdisk(name='vdisk', data=self.valid_data)
        vdisk.api.services.get = MagicMock()
        vdisk.validate()
        data = self.valid_data.copy()
        data['zerodb'] = ''
        data['nsName'] = ''
        data['password'] = vdisk.data['password']
        assert vdisk.data == data
        assert vdisk.data['password'] is not ''

    def test_zerodb_property(self):
        vdisk = Vdisk(name='vdisk', data=self.valid_data)
        vdisk.api.services.get = MagicMock(return_value='zerodb')
        assert vdisk._zerodb == 'zerodb'

    def test_install(self):
        vdisk = Vdisk(name='vdisk', data=self.valid_data)
        node = MagicMock()
        node.schedule_action = MagicMock(return_value=task_mock(('instance', 'ns_name')))
        vdisk.api = MagicMock()
        vdisk.api.services.get = MagicMock(return_value=node)
        vdisk.install()
        args = {
            'disktype': vdisk.data['diskType'].upper(),
            'mode': 'user',
            'password': vdisk.data['password'],
            'public': False,
            'size': int(vdisk.data['size']),
        }
        node.schedule_action.assert_called_once_with('create_zdb_namespace', args)
        vdisk.state.check('actions', 'install', 'ok')
        assert vdisk.data['nsName'] == 'ns_name'
        assert vdisk.data['zerodb'] == 'instance'

    def test_info_without_install(self):
        with pytest.raises(StateCheckError, message='Executing info action without install should raise an error'):
            vdisk = Vdisk(name='vdisk', data=self.valid_data)
            vdisk.info()

    def test_info(self):
        vdisk = Vdisk(name='vdisk', data=self.valid_data)
        vdisk.data['nsName'] = 'ns_name'
        vdisk.state.set('actions', 'install', 'ok')
        vdisk.api = MagicMock()
        task = task_mock('info')
        vdisk._zerodb.schedule_action = MagicMock(return_value=task)

        assert vdisk.info() == 'info'
        vdisk._zerodb.schedule_action.assert_called_once_with('namespace_info', args={'name': vdisk.data['nsName']})

    def test_uninstall(self):
        vdisk = Vdisk(name='vdisk', data=self.valid_data)
        vdisk.data['nsName'] = 'ns_name'
        vdisk.state.set('actions', 'install', 'ok')
        vdisk.api = MagicMock()
        vdisk.uninstall()
        vdisk._zerodb.schedule_action.assert_called_once_with('namespace_delete', args={'name': 'ns_name'})

    def test_url_without_install(self):
        with pytest.raises(StateCheckError, message='Executing info action without install should raise an error'):
            vdisk = Vdisk(name='vdisk', data=self.valid_data)
            vdisk.url()

    def test_url(self):
        vdisk = Vdisk(name='vdisk', data=self.valid_data)
        vdisk.data['nsName'] = 'ns_name'
        vdisk.state.set('actions', 'install', 'ok')
        vdisk.api = MagicMock()
        vdisk._zerodb.schedule_action = MagicMock(return_value=task_mock('url'))

        assert vdisk.url() == 'url'
        vdisk._zerodb.schedule_action.assert_called_once_with('namespace_url', args={'name': 'ns_name'})

    def test_private_url_without_install(self):
        with pytest.raises(StateCheckError, message='Executing info action without install should raise an error'):
            vdisk = Vdisk(name='vdisk', data=self.valid_data)
            vdisk.url()

    def test_private_url(self):
        vdisk = Vdisk(name='vdisk', data=self.valid_data)
        vdisk.data['nsName'] = 'ns_name'
        vdisk.state.set('actions', 'install', 'ok')
        vdisk.api = MagicMock()
        vdisk._zerodb.schedule_action = MagicMock(return_value=task_mock('url'))

        assert vdisk.private_url() == 'url'
        vdisk._zerodb.schedule_action.assert_called_once_with('namespace_private_url', args={'name': 'ns_name'})
