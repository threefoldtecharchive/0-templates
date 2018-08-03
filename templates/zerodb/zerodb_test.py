from unittest.mock import MagicMock, patch, call
import copy
import os
import pytest

from zerodb import Zerodb, NODE_CLIENT
from zerorobot.template.state import StateCheckError
from zerorobot.service_collection import ServiceNotFoundError

from JumpscaleZrobot.test.utils import ZrobotBaseTest


class TestZerodbTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), Zerodb)

    def setUp(self):
        self.valid_data = {
            'nodePort': 9900,
            'mode': 'user',
            'sync': False,
            'admin': '',
            'path': '/dev/sda1',
            'namespaces': [],
            'ztIdentity': '',
            'nics': [],
        }
        patch('jumpscale.j.sal_zos', MagicMock()).start()

    def tearDown(self):
        patch.stopall()

    def test_create_valid_data(self):
        zdb = Zerodb('zdb', data=self.valid_data)
        zdb.validate()
        assert zdb.data == self.valid_data

    def test_node_sal(self):
        """
        Test _node_sal property
        """
        get_node = patch('jumpscale.j.clients.zos.get', MagicMock(return_value='node_sal')).start()
        zdb = Zerodb('zdb', data=self.valid_data)

        assert zdb._node_sal == 'node_sal'
        get_node.assert_called_once_with(NODE_CLIENT)

    def test_zerodb_sal(self):
        """
        Test _zerodb_sal property
        """
        zdb = Zerodb('zdb', data=self.valid_data)
        self.valid_data['name'] = zdb.name
        zdb_sal = MagicMock()
        zdb._node_sal.primitives.from_dict.return_value = zdb_sal

        assert zdb._zerodb_sal == zdb_sal
        zdb._node_sal.primitives.from_dict.assert_called_once_with('zerodb', self.valid_data)

    def test_install_empty_password(self):
        """
        Test install action sets admin password if empty
        """
        zdb = Zerodb('zdb', data=self.valid_data)

        zdb.install()
        zdb._zerodb_sal.deploy.called_once_with()
        zdb.state.check('actions', 'install', 'ok')
        assert zdb.data['admin'] != ''

    def test_install_with_password(self):
        """
        Test install action with admin password
        """
        data = self.valid_data.copy()
        data['admin'] = 'password'
        zdb = Zerodb('zdb', data=data)

        zdb.install()
        zdb._zerodb_sal.deploy.called_once_with()

        zdb.state.check('actions', 'install', 'ok')
        assert zdb.data['admin'] == 'password'

    def test_start_before_install(self):
        """
        Test start action without installing
        """
        with pytest.raises(StateCheckError,
                           message='start action should raise an error if zerodb is not installed'):
            zdb = Zerodb('zdb', data=self.valid_data)
            zdb.start()

    def test_stop(self):
        """
        Test stop action
        """
        zdb = Zerodb('zdb', data=self.valid_data)
        zdb.stop()

        zdb._zerodb_sal.stop.assert_called_once_with()
        with pytest.raises(StateCheckError, message='state status/running should not be present after stop'):
            zdb.state.check('status', 'running', 'ok')
        with pytest.raises(StateCheckError, message='state action/install should not be present after stop'):
            zdb.state.check('actions', 'start', 'ok')

    def test_stop_before_start(self):
        """
        Test stop action without install
        """
        zdb = Zerodb('zdb', data=self.valid_data)
        zdb.stop()
        # should be a no op if the zerodb is already stopped

    def test_namespace_list_before_start(self):
        """
        Test namespace_list action without start
        """
        with pytest.raises(StateCheckError,
                           message='namespace_list action should raise an error if zerodb is not started'):
            zdb = Zerodb('zdb', data=self.valid_data)
            zdb.namespace_list()

    def test_namespace_list(self):
        """
        Test namespace_list action
        """
        zdb = Zerodb('zdb', data=self.valid_data)
        zdb.state.set('status', 'running', 'ok')
        namespaces = zdb.namespace_list()
        assert namespaces == zdb.data['namespaces']

    def test_namespace_info_before_start(self):
        """
        Test namespace_info action without start
        """
        with pytest.raises(StateCheckError,
                           message='namespace action should raise an error if zerodb is not started'):
            zdb = Zerodb('zdb', data=self.valid_data)
            zdb.namespace_info('namespace')

    def test_namespace_info_doesnt_exist(self):
        """
        Test namespace_info action without start
        """
        with pytest.raises(LookupError,
                           message='namespace action should raise an error if namespace doesnt exist'):
            zdb = Zerodb('zdb', data=self.valid_data)
            zdb.state.set('status', 'running', 'ok')
            zdb.namespace_info('namespace')

    def test_namespace_info(self):
        """
        Test namespace_info action
        """
        self.valid_data['namespaces'].append({'name': 'namespace', 'size': 20, 'public': True, 'password': ''})

        zdb = Zerodb('zdb', data=self.valid_data)
        info_dict = {
            'data_limits_bytes': 21474836480,
            'data_size_bytes': 0,
            'data_size_mb': 0.0,
            'entries': 0,
            'index_size_bytes': 0,
            'index_size_kb': 0.0,
            'name': 'two',
            'password': 'yes',
            'public': 'yes'
        }
        zdb.state.set('status', 'running', 'ok')
        namespace = MagicMock()
        namespace.info.return_value.to_dict.return_value = info_dict
        zdb_sal = MagicMock(namespaces={'namespace': namespace})
        zdb._node_sal.primitives.from_dict.return_value = zdb_sal

        assert zdb.namespace_info('namespace') == info_dict

    def test_namespace_create_before_start(self):
        """
        Test namespace_create action without start
        """
        with pytest.raises(StateCheckError,
                           message='namespace_create action should raise an error if zerodb is not started'):
            zdb = Zerodb('zdb', data=self.valid_data)
            zdb.namespace_create('namespace')

    def test_namespace_create(self):
        """
        Test namespace_set action
        """
        zdb = Zerodb('zdb', data=self.valid_data)
        zdb.state.set('status', 'running', 'ok')
        zdb._deploy = MagicMock()
        zdb._namespace_exists_update_delete = MagicMock(return_value=False)
        zdb.namespace_create('namespace', 12, 'secret')

        zdb._zerodb_sal.deploy.assert_called_once_with()
        zdb._namespace_exists_update_delete.assert_called_once_with('namespace')
        assert zdb.data['namespaces'] == [{
            'name': 'namespace', 'size': 12, 'password': 'secret', 'public': True
        }]

    def test_namespace_create_namespace_exists(self):
        """
        Test namespace_set action
        """
        with pytest.raises(ValueError,
                           message='namespace_create action should raise an error if namespace exists'):
            zdb = Zerodb('zdb', data=self.valid_data)
            zdb.state.set('status', 'running', 'ok')
            zdb._deploy = MagicMock()
            zdb._namespace_exists_update_delete = MagicMock(return_value=True)
            zdb.namespace_create('namespace', 12, 'secret')

    def test_namespace_set_before_start(self):
        """
        Test namespace_set action without start
        """
        with pytest.raises(StateCheckError,
                           message='namespace_set action should raise an error if zerodb is not started'):
            zdb = Zerodb('zdb', data=self.valid_data)
            zdb.namespace_set('namespace', 'size', 12)

    def test_namespace_set(self):
        """
        Test namespace_set action
        """
        zdb = Zerodb('zdb', data=self.valid_data)
        zdb.state.set('status', 'running', 'ok')
        zdb._namespace_exists_update_delete = MagicMock(return_value=True)
        zdb._deploy = MagicMock()
        zdb.namespace_set('namespace', 'size', 12)
        zdb._zerodb_sal.deploy.assert_called_once_with()

    def test_namespace_set_namespace_doesnt_exist(self):
        """
        Test namespace_set action if namespace doesn't exist
        """
        with pytest.raises(LookupError,
                           message='namespace_set action should raise an error if namespace doesn\'t exists'):
            zdb = Zerodb('zdb', data=self.valid_data)
            zdb.state.set('status', 'running', 'ok')
            zdb._namespace_exists_update_delete = MagicMock(return_value=False)
            zdb.namespace_set('namespace', 'size', 12)

    def test_namespace_delete_before_start(self):
        """
        Test namespace_delete action without start
        """
        with pytest.raises(StateCheckError,
                           message='namespace_delete action should raise an error if zerodb is not started'):
            zdb = Zerodb('zdb', data=self.valid_data)
            zdb.namespace_delete('namespace')

    def test_namespace_delete(self):
        """
        Test namespace_delete action
        """
        zdb = Zerodb('zdb', data=self.valid_data)
        zdb.state.set('status', 'running', 'ok')
        zdb._namespace_exists_update_delete = MagicMock(return_value=True)
        zdb._deploy = MagicMock()
        zdb.namespace_delete('namespace')
        zdb._zerodb_sal.deploy.assert_called_once_with()

    def test_deploy(self):
        """
        Test _deploy helper function
        """
        zdb = Zerodb('zdb', data=self.valid_data)
        zdb_sal = MagicMock(node_port=9900, zt_identity='identity')

        zdb._node_sal.primitives.from_dict.return_value = zdb_sal
        zdb._deploy()
        assert zdb.data['ztIdentity'] == zdb_sal.zt_identity
        assert zdb.data['nodePort'] == zdb_sal.node_port

    def test_connection_info(self):
        """
        Test connection_info action
        """
        zdb = Zerodb('zdb', data=self.valid_data)
        node_sal = MagicMock(public_addr='127.0.0.1')
        patch('jumpscale.j.clients.zos.get', MagicMock(return_value=node_sal)).start()
        assert zdb.connection_info() == {
            'ip': node_sal.public_addr,
            'port': zdb.data['nodePort'],
        }

    def test_namespace_exist_update_delete_runtimeerror(self):
        """
        Test _namespace_exists_update_delete raises RunTimeError if you try to update and delete a namespace at the same time
        """
        with pytest.raises(ValueError,
                           message='_namespace_exist_update_delete action should raise an error if user is trying to set property and delete namespace'):
            zdb = Zerodb('zdb', data=self.valid_data)
            zdb._namespace_exists_update_delete('namespace', prop='password', delete=True)

    def test_namespace_exist_update_delete_invalid_property(self):
        """
        Test _namespace_exists_update_delete raises ValueError if you supply invalid prop
        """
        with pytest.raises(ValueError,
                           message='_namespace_exist_update_dekete action should raise an error if user uses invalid prop'):
            zdb = Zerodb('zdb', data=self.valid_data)
            zdb._namespace_exists_update_delete('namespace', prop='prop')

    def test_namespace_exist_update_delete_doesnt_exist(self):
        """
        Test _namespace_exists_update_delete if namespace doesn't exist
        """
        zdb = Zerodb('zdb', data=self.valid_data)
        assert zdb._namespace_exists_update_delete('namespace') is False

    def test_namespace_exist_update_delete_exists(self):
        """
        Test _namespace_exists_update_delete if namespace exists
        """
        self.valid_data['namespaces'].append({'name': 'namespace', 'size': 20, 'public': True, 'password': ''})
        zdb = Zerodb('zdb', data=self.valid_data)
        assert zdb._namespace_exists_update_delete('namespace') is True

    def test_namespace_exist_update_delete_update_prop(self):
        """
        Test _namespace_exists_update_delete if namespace exists and prop is updated
        """
        self.valid_data['namespaces'].append({'name': 'namespace', 'size': 20, 'public': True, 'password': ''})
        zdb = Zerodb('zdb', data=self.valid_data)
        assert zdb._namespace_exists_update_delete('namespace', prop='size', value=30) is True
        assert zdb.data['namespaces'] == [{'name': 'namespace', 'size': 30, 'public': True, 'password': ''}]

    def test_namespace_exist_update_delete_namespace_delete(self):
        """
        Test _namespace_exists_update_delete if namespace exists and prop
        """
        self.valid_data['namespaces'].append({'name': 'namespace', 'size': 20, 'public': True, 'password': ''})
        zdb = Zerodb('zdb', data=self.valid_data)
        assert zdb._namespace_exists_update_delete('namespace', delete=True) is True
        assert zdb.data['namespaces'] == []

    def test_namespace_url_before_start(self):
        """
        Test namespace_url action without start
        """
        with pytest.raises(StateCheckError,
                           message='namespace action should raise an error if zerodb is not started'):
            zdb = Zerodb('zdb', data=self.valid_data)
            zdb.namespace_url('namespace')

    def test_namespace_url_doesnt_exist(self):
        """
        Test namespace_url action without start
        """
        with pytest.raises(LookupError,
                           message='namespace action should raise an error if namespace doesnt exist'):
            zdb = Zerodb('zdb', data=self.valid_data)
            zdb.state.set('status', 'running', 'ok')
            zdb.namespace_url('namespace')

    def test_namespace_url(self):
        """
        Test namespace_url action
        """
        self.valid_data['namespaces'].append({'name': 'namespace', 'size': 20, 'public': True, 'password': ''})

        zdb = Zerodb('zdb', data=self.valid_data)
        zdb.state.set('status', 'running', 'ok')
        namespace = MagicMock(url='url')
        zdb_sal = MagicMock(namespaces={'namespace': namespace})
        zdb._node_sal.primitives.from_dict.return_value = zdb_sal

        assert zdb.namespace_url('namespace') == 'url'

    def test_namespace_private_url_before_start(self):
        """
        Test namespace_private_url action without start
        """
        with pytest.raises(StateCheckError,
                           message='namespace action should raise an error if zerodb is not started'):
            zdb = Zerodb('zdb', data=self.valid_data)
            zdb.namespace_private_url('namespace')

    def test_namespace_private_url_doesnt_exist(self):
        """
        Test namespace_private_url action without start
        """
        with pytest.raises(LookupError,
                           message='namespace action should raise an error if namespace doesnt exist'):
            zdb = Zerodb('zdb', data=self.valid_data)
            zdb.state.set('status', 'running', 'ok')
            zdb.namespace_private_url('namespace')

    def test_namespace_private_url(self):
        """
        Test namespace_url action
        """
        self.valid_data['namespaces'].append({'name': 'namespace', 'size': 20, 'public': True, 'password': ''})

        zdb = Zerodb('zdb', data=self.valid_data)
        zdb.state.set('status', 'running', 'ok')
        namespace = MagicMock(private_url='url')
        zdb_sal = MagicMock(namespaces={'namespace': namespace})
        zdb._node_sal.primitives.from_dict.return_value = zdb_sal

        assert zdb.namespace_private_url('namespace') == 'url'

    def test_monitor_started(self):
        """
        Test _monitor action when zerodb should be started and it can be started
        """
        node = MagicMock()
        node.state.check.return_value = True

        zdb = Zerodb('zdb', data=self.valid_data)
        zdb.api.services.get = MagicMock(return_value=node)

        zdb._zerodb_sal.is_running = MagicMock(side_effect=[(False,), (True,)])
        zdb.state.set('actions', 'install', 'ok')
        zdb.state.set('actions', 'start', 'ok')
        zdb._monitor()
        zdb.state.check('status', 'running', 'ok')

    def test_monitor_started_cant_restart(self):
        """
        Test _monitor action when zerodb should be started and it cannot be re-started
        """
        node = MagicMock()
        node.state.check.return_value = True

        zdb = Zerodb('zdb', data=self.valid_data)
        zdb.api.services.get = MagicMock(return_value=node)

        zdb._zerodb_sal.is_running = MagicMock(side_effect=[(False,), (False,)])
        zdb.state.set('actions', 'install', 'ok')
        zdb.state.set('actions', 'start', 'ok')
        zdb._monitor()
        with pytest.raises(StateCheckError):
            zdb.state.check('status', 'running', 'ok')

    def test_monitor_not_started(self):
        """
        Test _monitor action when zerodb is not started
        """
        zdb = Zerodb('zdb', data=self.valid_data)
        zdb.state.set('actions', 'install', 'ok')
        with pytest.raises(StateCheckError, message='_monitor should not start zerodb is the start action has not been called'):
            zdb._monitor()
        with pytest.raises(StateCheckError, message='_monitor should not start zerodb is the start action has not been called'):
            zdb.state.check('status', 'running', 'ok')
