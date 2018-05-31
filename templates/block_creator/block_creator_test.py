from unittest import TestCase
from unittest.mock import MagicMock, patch, call
import tempfile
import shutil
import os

import pytest

from js9 import j

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
patch("time.sleep", MagicMock()).start()


class TestBlockCreatorTemplate(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.valid_data = {
            'node': 'node',
            'rpcPort': 23112,
            'apiPort': 23110,
            'walletAddr': '',
            'walletSeed': '',
            'walletPassphrase': 'walletPassphrase',
            'network': 'standard',
            'parentInterface': '',
            'tfchainFlist': 'https://hub.gig.tech/tfchain/ubuntu-16.04-tfchain-latest.flist',
        }
        config.DATA_DIR = tempfile.mkdtemp(prefix='0-templates_')
        cls.type = template_collection._load_template(
            "https://github.com/threefoldtoken/0-templates",
            os.path.dirname(__file__)
        )


    @classmethod
    def tearDownClass(cls):
        if os.path.exists(config.DATA_DIR):
            shutil.rmtree(config.DATA_DIR)

    def setUp(self):
        self.client_get = patch('js9.j.clients', MagicMock()).start()

    def tearDown(self):
        patch.stopall()

    def test_create_with_valid_data(self):
        """
        Test create blockcreator service
        """
        bc = self.type(name='blockcreator', data=self.valid_data)
        bc.validate()
        assert bc.data == self.valid_data

    def test_create_with_custom_network(self):
        """
        Test create explorer service
        """
        valid_data = self.valid_data.copy()
        valid_data['network'] = 'testnet'
        bc = self.type(name='blockcreator', data=valid_data)
        bc.validate()
        assert bc.data == valid_data

    def test_node_sal(self):
        """
        Test node_sal property
        """
        get_node = patch('js9.j.clients.zero_os.sal.get_node', MagicMock(return_value='node_sal')).start()
        bc = self.type(name='blockcreator', data=self.valid_data)
        node_sal = bc._node_sal
        get_node.assert_called_with(bc.data['node'])
        assert node_sal == 'node_sal'

    def test_install(self):
        """
        Test node install
        """
        bc = self.type(name='blockcreator', data=self.valid_data)
        bc._daemon_sal.start = MagicMock()
        bc.api.services.find_or_create = MagicMock()
        fs = MagicMock(path='/var/cache')
        sp = MagicMock()
        sp.get = MagicMock(return_value=fs)
        bc._node_sal.storagepools.get = MagicMock(return_value=sp)
        list_of_candidates = [{'gw': '1.1.1.1', 'dev': 'one'}]
        bc._node_sal.client.ip.route.list = MagicMock(return_value=list_of_candidates)

        bc.api.services.find_or_create.return_value.state.check = MagicMock(side_effect=StateCheckError)

        bc.install()

        container_data = {
            'flist': 'https://hub.gig.tech/tfchain/ubuntu-16.04-tfchain-latest.flist',
            'node': bc.data['node'],
            'nics': [{'type': 'macvlan', 'id': 'one', 'config': {'dhcp': True}, 'name': 'stoffel'}],
            'mounts': [
                {'source': '/var/cache/wallet',
                 'target': '/mnt/data'}
            ],
        }
        # test creation of container
        bc.api.services.find_or_create.assert_called_once_with(
            'github.com/zero-os/0-templates/container/0.0.1', 
            bc._container_name,
            data=container_data)

        bc.state.check('actions', 'install', 'ok')
        assert bc.api.services.find_or_create.return_value.schedule_action.call_count == 2

    def test_start_not_installed(self):
        with pytest.raises(StateCheckError,
                           message='start action should raise an error if explorer is not installed'):
            bc = self.type(name='blockcreator', data=self.valid_data)
            bc.start()

    def test_start_installed_wallet_not_inited(self):
        bc = self.type(name='blockcreator', data=self.valid_data)

        bc.state.set('actions', 'install', 'ok')
        bc.api.services.find_or_create = MagicMock()

        bc._daemon_sal.start = MagicMock()
        bc._client_sal.wallet_init = MagicMock()
        bc._client_sal.wallet_unlock = MagicMock()
        list_of_candidates = [{'gw': '1.1.1.1', 'dev': 'one'}]
        bc._node_sal.client.ip.route.list = MagicMock(return_value=list_of_candidates)

        bc.start()

        bc.state.check('actions', 'start', 'ok')
        bc.state.check('status', 'running', 'ok')
        bc.state.check('wallet', 'init', 'ok')
        bc.state.check('wallet', 'unlock', 'ok')

        bc._daemon_sal.start.assert_called_once_with()
        bc._client_sal.wallet_init.assert_called_once_with()
        bc._client_sal.wallet_unlock.assert_called_once_with()
        assert bc.data['walletSeed'] != ''

    def test_start_installed_wallet_inited(self):
        bc = self.type(name='blockcreator', data=self.valid_data)

        bc.state.set('actions', 'install', 'ok')
        bc.state.set('wallet', 'init', 'ok')
        bc.api.services.find_or_create = MagicMock()
        bc._daemon_sal.start = MagicMock()
        bc._client_sal.wallet_init = MagicMock()
        list_of_candidates = [{'gw': '1.1.1.1', 'dev': 'one'}]
        bc._node_sal.client.ip.route.list = MagicMock(return_value=list_of_candidates)
        bc._client_sal.wallet_unlock = MagicMock()
        bc.start()

        bc.state.check('actions', 'start', 'ok')
        bc.state.check('status', 'running', 'ok')
        bc.state.check('wallet', 'init', 'ok')
        bc.state.check('wallet', 'unlock', 'ok')

        bc._daemon_sal.start.assert_called_once_with()
        bc._client_sal.wallet_init.assert_not_called()
        bc._client_sal.wallet_unlock.assert_called_with()
        assert bc._client_sal.wallet_unlock.called

    def test_uninstall(self):
        bc = self.type(name='blockcreator', data=self.valid_data)

        container = MagicMock()
        container.schedule_action = MagicMock()
        container.delete = MagicMock()

        bc.stop = MagicMock()
        bc.api.services.find_or_create = MagicMock()
        bc.api.services.get = MagicMock(return_value=container)
        fs = MagicMock()
        fs.delete = MagicMock()
        sp = MagicMock()
        sp.get = MagicMock(return_value=fs)
        bc._node_sal.storagepools.get = MagicMock(return_value=sp)

        bc.uninstall()

        with pytest.raises(StateCheckError):
            bc.state.check('actions', 'install', 'ok')
        with pytest.raises(StateCheckError):
            bc.state.check('status', 'running', 'ok')
        with pytest.raises(StateCheckError):
            bc.state.check('status', 'init', 'ok')
        with pytest.raises(StateCheckError):
            bc.state.check('wallet', 'unlock', 'ok')

        bc.stop.assert_called_once_with()
        sp.get.assert_called_once_with(bc.guid)
        fs.delete.assert_called_once_with()
        container.delete.assert_called_once_with()

    def test_uninstall_container_not_exists(self):
        bc = self.type(name='blockcreator', data=self.valid_data)

        bc.stop = MagicMock(side_effect=LookupError)
        bc.api.services.find_or_create = MagicMock()
        fs = MagicMock()
        fs.delete = MagicMock()
        sp = MagicMock()
        sp.get = MagicMock(return_value=fs)
        bc._node_sal.storagepools.get = MagicMock(side_effect=ValueError)

        bc.uninstall()

        with pytest.raises(StateCheckError):
            bc.state.check('actions', 'install', 'ok')
        with pytest.raises(StateCheckError):
            bc.state.check('status', 'running', 'ok')

        bc.stop.assert_called_once_with()
        sp.get.assert_not_called()
        fs.assert_not_called()

    def test_stop(self):
        container = MagicMock()
        container.schedule_action = MagicMock()
        container.delete = MagicMock()

        bc = self.type(name='blockcreator', data=self.valid_data)
        bc.state.set('actions', 'install', 'ok')

        bc.api.services.get = MagicMock(return_value=container)
        bc._daemon_sal.stop = MagicMock()

        bc.stop()

        with pytest.raises(StateCheckError):
            bc.state.check('actions', 'start', 'ok')
        with pytest.raises(StateCheckError):
            bc.state.check('status', 'running', 'ok')
        with pytest.raises(StateCheckError):
            bc.state.check('wallet', 'unlock', 'ok')

        bc._daemon_sal.stop.assert_called_once_with()
        container.schedule_action.assert_called_once_with('stop')
        container.delete.assert_not_called()

    def test_stop_container_not_exists(self):
        bc = self.type(name='blockcreator', data=self.valid_data)

        bc.state.set('actions', 'install', 'ok')

        container = MagicMock()
        container.schedule_action = MagicMock()
        container.delete = MagicMock()

        bc.api.services.get = MagicMock(return_value=container)
        bc._daemon_sal.stop = MagicMock(side_effect=LookupError)

        with self.assertRaises(RuntimeError):
            bc.stop()

        with pytest.raises(StateCheckError):
            bc.state.check('actions', 'start', 'ok')
        with pytest.raises(StateCheckError):
            bc.state.check('status', 'running', 'ok')

        bc._daemon_sal.stop.assert_called_once_with()
        container.schedule_action.assert_not_called()
        container.delete.assert_not_called()

    def test_upgrade_fail_no_candidates(self):
        bc = self.type(name='blockcreator', data=self.valid_data)
        bc._node_sal.storagepools.get = MagicMock()
        
        bc.stop = MagicMock()
        bc.start = MagicMock()

        container = MagicMock()
        container.schedule_action = MagicMock()
        container.delete = MagicMock()

        bc.api.services.get = MagicMock(return_value=container)
        bc._node_sal.client.nft.drop_port = MagicMock()
        
        with self.assertRaisesRegex(RuntimeError, 'Could not find interface for macvlan parent'):
            bc.upgrade()

    def test_upgrade_fail_too_many_candidates(self):
        bc = self.type(name='blockcreator', data=self.valid_data)
        bc._node_sal.storagepools.get = MagicMock()
        
        bc.stop = MagicMock()
        bc.start = MagicMock()

        container = MagicMock()
        container.schedule_action = MagicMock()
        container.delete = MagicMock()

        bc.api.services.get = MagicMock(return_value=container)
        bc._node_sal.client.nft.drop_port = MagicMock()
        list_of_candidates = [{'gw': '1.1.1.1', 'dev': 'one'}, {'gw': '1.1.1.2', 'dev':'two'}]
        bc._node_sal.client.ip.route.list = MagicMock(return_value=list_of_candidates)
        
        with self.assertRaisesRegex(RuntimeError, 'Found multiple eligible interfaces for macvlan parent: one, two'):
            bc.upgrade()

    def test_upgrade_success(self):
        bc = self.type(name='blockcreator', data=self.valid_data)
        bc._node_sal.storagepools.get = MagicMock()

        bc.stop = MagicMock()
        bc.start = MagicMock()

        container = MagicMock()
        container.schedule_action = MagicMock()
        container.delete = MagicMock()

        bc.api.services.get = MagicMock(return_value=container)
        bc._node_sal.client.nft.drop_port = MagicMock()
        
        list_of_candidates = [{'gw': '1.1.1.1', 'dev': 'one'}]
        bc._node_sal.client.ip.route.list = MagicMock(return_value=list_of_candidates)
        
        bc.upgrade()

        bc.stop.assert_called_once_with()
        bc.start.assert_called_once_with()
        bc._node_sal.client.nft.drop_port.assert_called_once_with(23112)

    def test_consensus_stat(self):
        bc = self.type(name='blockcreator', data=self.valid_data)
        bc.state.set('status', 'running', 'ok')

        bc._client_sal.consensus_stat = MagicMock()

        bc.consensus_stat()

        bc._client_sal.consensus_stat.assert_called_once_with()

    def test_consensus_stat_not_running(self):
        bc = self.type(name='blockcreator', data=self.valid_data)

        bc._client_sal.consensus_stat = MagicMock()

        with pytest.raises(StateCheckError):
            bc.consensus_stat()

        bc._client_sal.consensus_stat.assert_not_called()

    def test_wallet_amount(self):
        bc = self.type(name='blockcreator', data=self.valid_data)
        bc.state.set('status', 'running', 'ok')
        bc.state.set('wallet', 'init', 'ok')
        bc.state.set('wallet', 'unlock', 'ok')

        bc._client_sal.wallet_amount = MagicMock()

        bc.wallet_amount()

        bc._client_sal.wallet_amount.assert_called_once_with()

    def test_wallet_amount_wallet_not_unlocked(self):
        bc = self.type(name='blockcreator', data=self.valid_data)
        
        bc.state.set('status', 'running', 'ok')

        bc._client_sal.wallet_amount = MagicMock()

        with pytest.raises(StateCheckError):
            bc.wallet_amount()

        bc._client_sal.wallet_amount.assert_not_called()

    def test_wallet_amount_not_running(self):
        bc = self.type(name='blockcreator', data=self.valid_data)

        bc._client_sal.wallet_amount = MagicMock()

        with pytest.raises(StateCheckError):
            bc.wallet_amount()

        bc._client_sal.wallet_amount.assert_not_called()

    def test_monitor_not_intalled(self):
        bc = self.type(name='blockcreator', data=self.valid_data)
        with pytest.raises(StateCheckError):
            bc._monitor()

    def test_monitor_not_started(self):
        bc = self.type(name='blockcreator', data=self.valid_data)
        bc.state.set('actions', 'start', 'ok')
        with pytest.raises(StateCheckError):
            bc._monitor()

    def test_monitor_is_running(self):
        bc = self.type(name='blockcreator', data=self.valid_data)

        bc.state.set('actions', 'install', 'ok')
        bc.state.set('actions', 'start', 'ok')
        bc._daemon_sal.is_running = MagicMock(return_value=True)
        bc.api.services.get = MagicMock()

        bc._monitor()

        bc.state.check('status', 'running', 'ok')
        bc.api.services.get.assert_not_called()

    def test_monitor_not_running(self):
        bc = self.type(name='blockcreator', data=self.valid_data)

        bc.state.set('actions', 'install', 'ok')
        bc.state.set('actions', 'start', 'ok')
        bc._daemon_sal.is_running = MagicMock(return_value=False)
        container = MagicMock()
        container.delete = MagicMock()
        bc.api.services.get = MagicMock(return_value=container)
        bc.install = MagicMock()

        def set_running_state():
            bc.state.set('status', 'running', 'ok')
        bc.start = MagicMock(side_effect=set_running_state)

        bc._monitor()

        bc.state.check('status', 'running', 'ok')
        bc.api.services.get.assert_called_with(template_uid='github.com/zero-os/0-templates/container/0.0.1', name=bc._container_name)
        container.delete.assert_called_once_with()
        bc.install.assert_called_once_with()
        bc.start.assert_called_once_with()


    def test_create_backup_success(self):
        bc = self.type(name='blockcreator', data=self.valid_data)
        result_mock = MagicMock(state='SUCCESS')
        bc._container_sal.client.system = MagicMock(return_value=MagicMock(get=MagicMock(return_value=result_mock)))
        bc.create_backup()
        bc._container_sal.client.system.assert_called_once_with(
            'tar -zcf /var/backups/backup.tar.gz /mnt/data -P'
        )

    def test_create_backup_fail(self):
        bc = self.type(name='blockcreator', data=self.valid_data)
        result_mock = MagicMock(state='ERROR', stderr='error message', data='error data')
        bc._container_sal.client.system = MagicMock(return_value=MagicMock(get=MagicMock(return_value=result_mock)))
        with self.assertRaisesRegex(RuntimeError, 'error occurred when creating backup: error message \n '):
            bc.create_backup()

    def test_restore_backup_success(self):
        bc = self.type(name='blockcreator', data=self.valid_data)
        result_mock = MagicMock(state='SUCCESS')
        bc._container_sal.client.system = MagicMock(return_value=MagicMock(get=MagicMock(return_value=result_mock)))
        bc.restore_backup()
        bc._container_sal.client.system.assert_called_once_with(
            'tar -zxf /var/backups/backup.tar.gz -P'
        )

    def test_restore_backup_fail(self):
        bc = self.type(name='blockcreator', data=self.valid_data)
        result_mock = MagicMock(state='ERROR', stderr='error message', data='error data')
        bc._container_sal.client.system = MagicMock(return_value=MagicMock(get=MagicMock(return_value=result_mock)))
        with self.assertRaisesRegex(RuntimeError, 'error occurred when restoring backup: error message \n '):
            bc.restore_backup()            