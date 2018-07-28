from unittest import TestCase
from unittest.mock import MagicMock, patch, call
import tempfile
import shutil
import os

import pytest

from js9 import j
#from explorer import Explorer, CONTAINER_TEMPLATE_UID
from zerorobot import service_collection as scol
from zerorobot import config, template_collection
from zerorobot.template_uid import TemplateUID
from zerorobot.template.state import StateCheckError


def mockdecorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


patch("zerorobot.template.decorator.timeout", MagicMock(return_value=mockdecorator)).start()
patch("zerorobot.template.decorator.retry", MagicMock(return_value=mockdecorator)).start()
patch("gevent.sleep", MagicMock()).start()


class TestExplorerTemplate(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.valid_data = {
            'node': 'node',
            'rpcPort': 23112,
            'apiPort': 23110,
            'domain': 'explorer.tft.com',
            'network': 'standard',
            'explorerFlist': 'https://hub.gig.tech/tfchain/caddy-explorer-latest.flist',
            'tfchainFlist': 'https://hub.gig.tech/tfchain/ubuntu-16.04-tfchain-latest.flist',
            'macAddress': '',
            'parentInterface': '',
        }
        config.DATA_DIR = tempfile.mkdtemp(prefix='0-templates_')
        config.DATA_DIR = tempfile.mkdtemp(prefix='0-templates_')
        cls.type = template_collection._load_template(
            "https://github.com/threefoldtoken/0-templates",
            os.path.dirname(__file__)
        )
        #Explorer.template_uid = TemplateUID.parse('github.com/threefoldtoken/0-templates/%s/%s' % (Explorer.template_name, Explorer.version))

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(config.DATA_DIR):
            shutil.rmtree(config.DATA_DIR)

    def setUp(self):
        self.client_get = patch('js9.j.clients', MagicMock()).start()

    def tearDown(self):
        patch.stopall()

    def test_create_invalid_data(self):
        """
        Test Explorer creation with invalid data
        """
        with pytest.raises(ValueError,
                           message='template should fail to instantiate if data dict is missing the domain'):
            explorer = self.type(name='explorer')
            explorer.validate()

    def test_create_with_valid_data(self):
        """
        Test create explorer service
        """
        explorer = self.type(name='explorer', data=self.valid_data)
        explorer.validate()
        assert explorer.data == self.valid_data

    def test_create_with_custom_network(self):
        """
        Test create explorer service
        """
        valid_data = self.valid_data.copy()
        valid_data['network'] = 'testnet'
        explorer = self.type(name='explorer', data=valid_data)
        explorer.validate()

        assert explorer.data == valid_data

    def test_node_sal(self):
        """
        Test node_sal property
        """
        get_node = patch('js9.j.clients.zero_os.sal.get_node', MagicMock(return_value='node_sal')).start()
        explorer = self.type(name='explorer', data=self.valid_data)
        node_sal = explorer._node_sal
        get_node.assert_called_with(explorer.data['node'])
        assert node_sal == 'node_sal'

    def test_install(self):
        """
        Test node install
        """
        explorer = self.type(name='explorer', data=self.valid_data)
        explorer.api.services.find_or_create = MagicMock()
        explorer._explorer_sal.start = MagicMock()
        explorer._node_sal.client.ip.route.list = MagicMock(return_value=[{'gw': str, 'dev':str}])
        fs = MagicMock(path='/var/cache')
        sp = MagicMock()
        sp.get = MagicMock(return_value=fs)
        explorer._node_sal.storagepools.get = MagicMock(return_value=sp)
        explorer.install()

        container_data = {
            'flist': 'https://hub.gig.tech/tfchain/ubuntu-16.04-tfchain-latest.flist',
            'node': explorer.data['node'],
            'nics': [{'type': 'default'}],
            'mounts': [
                {'source': '/var/cache/explorer',
                'target': '/mnt/data'},
                {'source': '/var/cache/caddy-certs',
                'target': '/.caddy'},
                {'source': 'https://hub.gig.tech/tfchain/caddy-explorer-latest.flist',
                'target': '/mnt/explorer'}
            ],
        }

        container_data = {
            'mounts': [
                {'source': '/var/cache/explorer', 'target': '/mnt/data'},
                {'source': '/var/cache/caddy-certs', 'target': '/.caddy'},
                {'source': 'https://hub.gig.tech/tfchain/caddy-explorer-latest.flist', 'target': '/mnt/explorer'}
                ],
                'node': 'node', 'nics': [{'type': 'macvlan', 'config': {'dhcp': True}, 'id': str, 'name': 'stoffel'}], 
                'flist': 'https://hub.gig.tech/tfchain/ubuntu-16.04-tfchain-latest.flist'
            }
        explorer.api.services.find_or_create.assert_called_once_with(
            'github.com/zero-os/0-templates/container/0.0.1',
            explorer._container_name,
            data=container_data
            )
        explorer._explorer_sal.start.assert_called_once_with()
        explorer.state.check('actions', 'install', 'ok')
        assert explorer._node_sal.client.nft.open_port.mock_calls == [call(23112), call(443), call(80)]

    def test_start_not_installed(self):
        with pytest.raises(StateCheckError,
                           message='start action should raise an error if explorer is not installed'):
            explorer = self.type(name='explorer', data=self.valid_data)
            explorer.start()

    def test_start_installed(self):
        explorer = self.type(name='explorer', data=self.valid_data)

        explorer.state.set('actions', 'install', 'ok')
        explorer.api.services.find_or_create = MagicMock()
        explorer._node_sal.client.nft.open_port = MagicMock()
        explorer._explorer_sal.start = MagicMock()
        explorer.data['parentInterface'] = str
        explorer.start()

        explorer.state.check('actions', 'start', 'ok')
        explorer.state.check('status', 'running', 'ok')

        assert explorer._node_sal.client.nft.open_port.mock_calls == [call(23112), call(443), call(80)]
        explorer._explorer_sal.start.assert_called_once_with()

    def test_uninstall(self):
        explorer = self.type(name='explorer', data=self.valid_data)

        container = MagicMock()
        container.schedule_action = MagicMock()
        container.delete = MagicMock()

        explorer.stop = MagicMock()
        explorer.api.services.find_or_create = MagicMock()
        explorer.api.services.get = MagicMock(return_value=container)
        fs = MagicMock()
        fs.delete = MagicMock()
        sp = MagicMock()
        sp.get = MagicMock(return_value=fs)
        explorer._node_sal.storagepools.get = MagicMock(return_value=sp)

        explorer.uninstall()

        with pytest.raises(StateCheckError):
            explorer.state.check('actions', 'install', 'ok')
        with pytest.raises(StateCheckError):
            explorer.state.check('status', 'running', 'ok')

        sp.get.assert_called_once_with(explorer.guid)
        fs.delete.assert_called_once_with()
        container.delete.assert_called_once_with()

    def test_uninstall_container_not_exists(self):
        explorer = self.type(name='explorer', data=self.valid_data)

        explorer.stop = MagicMock(side_effect=LookupError)
        explorer.api.services.find_or_create = MagicMock()
        fs = MagicMock()
        fs.delete = MagicMock()
        sp = MagicMock()
        sp.get = MagicMock(return_value=fs)
        explorer._node_sal.storagepools.get = MagicMock(side_effect=ValueError)

        explorer.uninstall()

        with pytest.raises(StateCheckError):
            explorer.state.check('actions', 'install', 'ok')
        with pytest.raises(StateCheckError):
            explorer.state.check('status', 'running', 'ok')

        sp.get.assert_not_called()
        fs.assert_not_called()

    def test_stop(self):
        explorer = self.type(name='explorer', data=self.valid_data)

        explorer.state.set('actions', 'install', 'ok')

        container = MagicMock()
        container.schedule_action = MagicMock()
        container.delete = MagicMock()

        explorer.api.services.get = MagicMock(return_value=container)
        explorer._node_sal.client.nft.drop_port = MagicMock()
        explorer._explorer_sal.stop = MagicMock()

        explorer.stop()

        with pytest.raises(StateCheckError):
            explorer.state.check('actions', 'start', 'ok')
        with pytest.raises(StateCheckError):
            explorer.state.check('status', 'running', 'ok')

        assert explorer._node_sal.client.nft.drop_port.mock_calls == [call(23112), call(443), call(80)]
        explorer._explorer_sal.stop.assert_called_once_with()
        container.schedule_action.assert_called_once_with('stop')
        container.delete.assert_not_called()

    def test_stop_container_not_exists(self):
        explorer = self.type(name='explorer', data=self.valid_data)

        explorer.state.set('actions', 'install', 'ok')

        container = MagicMock()
        container.schedule_action = MagicMock()
        container.delete = MagicMock()

        explorer.api.services.get = MagicMock(return_value=container)
        explorer._node_sal.client.nft.drop_port = MagicMock()
        explorer._explorer_sal.stop = MagicMock(side_effect=LookupError)

        explorer.stop()

        with pytest.raises(StateCheckError):
            explorer.state.check('actions', 'start', 'ok')
        with pytest.raises(StateCheckError):
            explorer.state.check('status', 'running', 'ok')

        assert explorer._node_sal.client.nft.drop_port.mock_calls == [call(23112), call(443), call(80)]
        explorer._explorer_sal.stop.assert_called_once_with()
        container.schedule_action.assert_not_called()
        container.delete.assert_not_called()

    def test_upgrade(self):
        explorer = self.type(name='explorer', data=self.valid_data)
        explorer.stop = MagicMock()
        explorer.start = MagicMock()

        explorer.upgrade()

        explorer.stop.assert_called_once_with()
        explorer.start.assert_called_once_with()

    def test_consensus_stat(self):
        explorer = self.type(name='explorer', data=self.valid_data)
        explorer.state.set('status', 'running', 'ok')

        explorer._explorer_sal.consensus_stat = MagicMock()

        explorer.consensus_stat()

        explorer._explorer_sal.consensus_stat.assert_called_once_with()

    def test_consensus_stat_not_running(self):
        explorer = self.type(name='explorer', data=self.valid_data)

        explorer._explorer_sal.consensus_stat = MagicMock()

        with pytest.raises(StateCheckError):
            explorer.consensus_stat()

        explorer._explorer_sal.consensus_stat.assert_not_called()

    def test_gateway(self):
        explorer = self.type(name='explorer', data=self.valid_data)
        explorer.state.set('status', 'running', 'ok')

        explorer._explorer_sal.gateway_stat = MagicMock()

        explorer.gateway_stat()

        explorer._explorer_sal.gateway_stat.assert_called_once_with()

    def test_gateway_not_running(self):
        explorer = self.type(name='explorer', data=self.valid_data)

        explorer._explorer_sal.gateway_stat = MagicMock()

        with pytest.raises(StateCheckError):
            explorer.gateway_stat()

        explorer._explorer_sal.gateway_stat.assert_not_called()

    def test_monitor_not_intalled(self):
        explorer = self.type(name='explorer', data=self.valid_data)
        with pytest.raises(StateCheckError):
            explorer._monitor()

    def test_monitor_not_started(self):
        explorer = self.type(name='explorer', data=self.valid_data)
        explorer.state.set('actions', 'start', 'ok')
        with pytest.raises(StateCheckError):
            explorer._monitor()

    def test_monitor_is_running(self):
        explorer = self.type(name='explorer', data=self.valid_data)

        explorer.state.set('actions', 'install', 'ok')
        explorer.state.set('actions', 'start', 'ok')
        explorer._explorer_sal.explorer.is_running = MagicMock(return_value=True)
        explorer.api.services.get = MagicMock()
        explorer._monitor()

        explorer.state.check('status', 'running', 'ok')
        explorer.api.services.get.assert_not_called()

    def test_monitor_not_running(self):
        explorer = self.type(name='explorer', data=self.valid_data)

        explorer.state.set('actions', 'install', 'ok')
        explorer.state.set('actions', 'start', 'ok')
        explorer._explorer_sal.is_running = MagicMock(return_value=False)
        container = MagicMock()
        container.delete = MagicMock()
        explorer.api.services.get = MagicMock(return_value=container)
        explorer.install = MagicMock()

        def set_running_state():
            explorer.state.set('status', 'running', 'ok')
        explorer.start = MagicMock(side_effect=set_running_state)

        explorer._monitor()

        explorer.state.check('status', 'running', 'ok')
        explorer.api.services.get.assert_called_with(
            template_uid='github.com/zero-os/0-templates/container/0.0.1', 
            name=explorer._container_name
        )
        container.delete.assert_called_once_with()
        explorer.install.assert_called_once_with()
        explorer.start.assert_called_once_with()
