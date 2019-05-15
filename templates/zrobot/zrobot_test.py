from unittest.mock import MagicMock, patch
from jumpscale import j
import os
import pytest

from zrobot import Zrobot, NODE_CLIENT
from zerorobot.template.state import StateCheckError
from zerorobot import service_collection as scol

from JumpscaleZrobot.test.utils import ZrobotBaseTest


class TestZrobotTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), Zrobot)
        cls.valid_data = {
            'templates': [],
            'organization': None,
            'nics': [],
            'dataRepo': 'https://example.com/account/data',
            'configRepo': 'https://example.com/account/config',
            'sshkey': 'privdata',
            'autoPushInterval': 1,
            'flist': 'https://hub.grid.tf/gig-official-apps/zero-os-0-robot-latest.flist',
        }

    def setUp(self):
        patch('jumpscale.j.clients.zos.get', MagicMock()).start()

    def tearDown(self):
        patch.stopall()

    def test_invalid_data(self):
        """
        Test creating a zrobot with invalid data
        """
        with pytest.raises(ValueError, message='template should fail to instantiate if configRepo is sepcified without sshkey'):
            zrobot = Zrobot(name='zrobot', data={'configRepo': 'https://example.com/account/config'})
            zrobot.validate()

    def test_valid_data(self):
        """
        Test creating a zrobot service with valid data
        """
        zrobot = Zrobot('zrobot', data=self.valid_data)
        zrobot.api.services.get = MagicMock()
        zrobot.validate()

        valid_data = self.valid_data.copy()
        valid_data['port'] = 0
        assert zrobot.data == valid_data

    def test_node_sal(self):
        """
        Test the node_sal property
        """
        zrobot = Zrobot('zrobot', data=self.valid_data)
        node_sal_return = 'node_sal'
        patch('jumpscale.j.clients.zos.get',  MagicMock(return_value=node_sal_return)).start()
        node_sal = zrobot._node_sal

        assert node_sal == node_sal_return
        j.clients.zos.get.assert_called_with(NODE_CLIENT)

    def test_zrobot_sal(self):
        """
        Test the node_sal property
        """
        zrobot = Zrobot('zrobot', data=self.valid_data)
        zrobot_sal_return = 'zrobot_sal'
        patch('jumpscale.j.clients.zrobot.get',  MagicMock(return_value=zrobot_sal_return)).start()
        zrobot_sal = zrobot.zrobot_sal
        container_sal = zrobot._node_sal.containers.get(zrobot._container_name)
        kwargs = {
            'container': container_sal,
            'port': 6600,
            'template_repos': self.valid_data['templates'],
            'organization': self.valid_data['organization'],
            'data_repo': self.valid_data['dataRepo'],
            'config_repo': self.valid_data['configRepo'],
            'config_key': zrobot.sshkey_path,
            'auto_push': True,
            'auto_push_interval': 1,
        }
        assert zrobot_sal == zrobot_sal_return
        j.clients.zrobot.get.assert_called_with(**kwargs)

    def test_already_installed_no_force(self):
        """
        Test installation when already installed without force option
        """
        zrobot = Zrobot('zrobot', data=self.valid_data)
        zrobot.state.set('actions', 'install', 'ok')
        zrobot.install()
        container = MagicMock()
        zrobot._get_container = MagicMock(return_value=container)
        container.schedule_action.assert_not_called()

    def test_already_installed_force(self):
        """
        Test installation when already installed with force option
        """
        zrobot = Zrobot('zrobot', data=self.valid_data)
        container = MagicMock()
        zrobot._get_container = MagicMock(return_value=container)
        patch('jumpscale.j.clients.zos.get',  MagicMock()).start()
        patch('jumpscale.j.clients.zrobot.get',  MagicMock()).start()
        zrobot.state.set('actions', 'install', 'ok')
        zrobot.install(True)
        zrobot.state.check('actions', 'install', 'ok')
        zrobot.state.check('actions', 'start', 'ok')
        container.schedule_action.assert_called_once_with('install')

    def test_install(self):
        """
        Test successfully creating zrobot
        """
        zrobot = Zrobot('zrobot', data=self.valid_data)
        container = MagicMock()
        zrobot._get_container = MagicMock(return_value=container)
        patch('jumpscale.j.clients.zos.get',  MagicMock()).start()
        patch('jumpscale.j.clients.zrobot.get',  MagicMock()).start()
        zrobot.install()
        zrobot.state.check('actions', 'install', 'ok')
        zrobot.state.check('actions', 'start', 'ok')
        container.schedule_action.assert_called_once_with('install')

    def test_install_with_sshkey(self):
        """
        Test installing while using an sshkey
        """
        zrobot = Zrobot('zrobot', data=self.valid_data)
        container = MagicMock()
        zrobot._get_container = MagicMock(return_value=container)
        container.container_sal = MagicMock()
        container_sal = container.container_sal
        patch('jumpscale.j.clients.zos.get',  MagicMock()).start()
        patch('jumpscale.j.clients.zrobot.get',  MagicMock()).start()
        zrobot.install()
        zrobot.state.check('actions', 'install', 'ok')
        zrobot.state.check('actions', 'start', 'ok')
        container.schedule_action.assert_called_once_with('install')
        container_sal.upload_content.assert_called_once_with(zrobot.sshkey_path, zrobot.data['sshkey'])

    def test_start(self):
        zrobot = Zrobot('zrobot', data=self.valid_data)
        container = MagicMock()
        zrobot._get_container = MagicMock(return_value=container)
        patch('jumpscale.j.clients.zos.get',  MagicMock()).start()
        patch('jumpscale.j.clients.zrobot.get',  MagicMock()).start()
        zrobot.start()
        zrobot.state.check('actions', 'start', 'ok')
        container.schedule_action.assert_called_once_with('start')

    def test_stop_before_starting(self):
        """
        Test stopping without starting
        """
        with pytest.raises(StateCheckError, message='Stop before start should raise an error'):
            zrobot = Zrobot('zrobot', data=self.valid_data)
            zrobot.stop()

    def test_stop(self):
        zrobot = Zrobot('zrobot', data=self.valid_data)
        zrobot.api.services.get = MagicMock()
        patch('jumpscale.j.clients.zrobot.get',  MagicMock()).start()
        zrobot.state.set('actions', 'start', 'ok')
        zrobot.state.delete = MagicMock(return_value=True)
        zrobot.stop()
        zrobot.state.delete.assert_called_with('status', 'running')

    def test_uninstall(self):
        zrobot = Zrobot('zrobot', data=self.valid_data)
        container = MagicMock()
        zrobot.api.services.get = MagicMock(return_value=container)
        patch('jumpscale.j.clients.zrobot.get',  MagicMock()).start()
        zrobot.state.set('actions', 'install', 'ok')
        zrobot.state.delete = MagicMock(return_value=True)
        zrobot.uninstall()
        zrobot.state.delete.assert_called_with('status', 'running')
        container.schedule_action.assert_called_once_with('uninstall')
        container.delete.assert_called_once_with()

    def test_monitor_service_ok(self):
        """
        Test monitor when container service exists
        """
        zrobot = Zrobot('zrobot', data=self.valid_data)
        zrobot.api.services.get = MagicMock()
        patch('jumpscale.j.clients.zrobot.get',  MagicMock()).start()
        zrobot.state.set('actions', 'install', 'ok')
        zrobot.state.set('actions', 'start', 'ok')
        zrobot._monitor()
        zrobot.state.check('status', 'running', 'ok')

    def test_monitor_service_not_found(self):
        """
        Test monitor when service container can't be found
        """
        zrobot = Zrobot('zrobot', data=self.valid_data)
        zrobot.api.services.get = MagicMock(side_effect=scol.ServiceNotFoundError())
        patch('jumpscale.j.clients.zrobot.get',  MagicMock()).start()
        zrobot.state.set('actions', 'install', 'ok')
        zrobot.state.set('actions', 'start', 'ok')
        zrobot.state.delete = MagicMock(return_value=True)
        zrobot.start = MagicMock()
        zrobot._monitor()
        zrobot.state.delete.assert_called_with('status', 'running')
        zrobot.start.assert_called_once_with()
