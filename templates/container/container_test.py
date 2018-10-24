from unittest.mock import MagicMock, patch
import os

import pytest

from container import Container
from zerorobot.template.state import StateCheckError
from zerorobot import service_collection as scol

from JumpscaleZrobot.test.utils import ZrobotBaseTest


class TestContainerTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), Container)
        cls.valid_data = {
            'bridges': [],
            'env': {},
            'flist': 'flist',
            'hostNetworking': False,
            'hostname': '',
            'ztIdentity': '',
            'initProcesses': [],
            'mounts': [],
            'nics': [],
            'ports': ['80:80'],
            'privileged': False,
            'storage': '',
            'zerotierNetwork': ''
        }

    def setUp(self):
        patch('jumpscale.j.clients.zos.get', MagicMock()).start()

    def tearDown(self):
        patch.stopall()

    def test_create_invalid_data(self):
        """
        Test Container creation with invalid data
        """
        with pytest.raises(ValueError, message='template should fail to instantiate if data dict is missing the flist'):
            container = Container(name='container')
            container.validate()

    def test_create_valid_data(self):
        container = Container(name='container', data=self.valid_data)
        container.validate()
        assert container.data == self.valid_data

    def test_node_sal(self):
        """
        Test the node_sal property
        """
        get_node = patch('jumpscale.j.clients.zos.get', MagicMock(return_value='node')).start()
        container = Container('container', data=self.valid_data)
        node_sal = container._node_sal
        assert get_node.called
        assert node_sal == 'node'

    def test_container_sal_container_installed(self):
        """
        Test container_sal property when container is exists
        """
        container = Container('container', data=self.valid_data)
        container._container = 'container'
        container.install = MagicMock()
        container_sal = container._container_sal

        assert container_sal == container._container
        assert container.install.called is False

    def test_container_sal_container_not_installed(self):
        """
        Test container_sal property when container doesn't exist
        """
        container = Container('container', data=self.valid_data)
        container.install = MagicMock()
        container._node_sal.containers.get.return_value = 'container'

        assert container._container_sal == 'container'

    def test_install_container_success(self):
        """
        Test successfully installing a container
        """
        container = Container('container', data=self.valid_data)
        container.api.services.get = MagicMock()
        container._node_sal.containers.create = MagicMock()

        container.install()

        container.state.check('actions', 'start', 'ok')
        assert container._node_sal.containers.create.called
        assert container._node_sal.containers.create.call_args[1]['ports'] == {'80': 80}, \
            "ports forward list should have been converted to dict"

    def test_start_container_before_install(self):
        """
        Test starting a container without installing first
        """
        with pytest.raises(StateCheckError, message='Starting container before install should raise an error'):
            container = Container('container', data=self.valid_data)
            container.start()

    def test_start_container_after_install(self):
        """
        Test successfully starting a container
        """
        container = Container('container', data=self.valid_data)
        container.state.set('actions', 'install', 'ok')
        container.start()

        assert container.state.check('actions', 'start', 'ok')
        assert container._container_sal.start.called

    def test_stop_container_before_install(self):
        """
        Test stopping a container without installing
        """
        with pytest.raises(StateCheckError, message='Stopping container before install should raise an error'):
            container = Container('container', data=self.valid_data)
            container.stop()

    def test_stop_container(self):
        """
        Test successfully stopping a container
        """
        container = Container('container', data=self.valid_data)
        container.state.set('actions', 'install', 'ok')
        container.state.delete = MagicMock(return_value=True)

        container.stop()

        assert container._container_sal.stop.called
        container.state.delete.assert_called_once_with('actions', 'start')

    def test_uninstall_container_before_install(self):
        """
        Test uninstall a container without installing
        """
        with pytest.raises(StateCheckError, message='Uninstall container before install should raise an error'):
            container = Container('container', data=self.valid_data)
            container.uninstall()

    def test_uninstall_container(self):
        """
        Test successfully uninstall a container
        """
        container = Container('container', data=self.valid_data)
        container.state.set('actions', 'install', 'ok')
        container.state.delete = MagicMock(return_value=True)
        container.stop = MagicMock()

        container.uninstall()

        container.stop.assert_called_once_with()
        container.state.delete.assert_called_once_with('actions', 'install')
