import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pytest

from Jumpscale import j
from JumpscaleZrobot.test.utils import ZrobotBaseTest
from minio import (LOG_LVL_CRITICAL_ERROR, LOG_LVL_JOB, LOG_LVL_LOG_STRUCTURED,
                   LOG_LVL_LOG_UNKNOWN, LOG_LVL_MESSAGE_INTERNAL,
                   LOG_LVL_MESSAGE_PUBLIC, LOG_LVL_OPS_ERROR,
                   LOG_LVL_RESULT_HRD, LOG_LVL_RESULT_JSON,
                   LOG_LVL_RESULT_TOML, LOG_LVL_RESULT_YAML,
                   LOG_LVL_STATISTICS, LOG_LVL_STDERR, LOG_LVL_STDOUT,
                   LOG_LVL_WARNING, NODE_CLIENT, Minio, _health_monitoring)
from zerorobot.template.state import (SERVICE_STATE_ERROR, SERVICE_STATE_OK,
                                      SERVICE_STATE_SKIPPED,
                                      SERVICE_STATE_WARNING, ServiceState,
                                      StateCheckError)


class TestMinioTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), Minio)
        cls.valid_data = {
            'container': 'container_minio',
            'node': 'node',
            'listenPort': 9000,
            'namespace': 'namespace',
            'nsSecret': 'nsSecret',
            'login': 'login',
            'password': 'password',
            'zerodbs': ['192.24.121.42:9900'],
            'privateKey': '',
            'metaPrivateKey': '1234567890abcdef',
            'blockSize': 1048576,
            'dataShard': 1,
            'parityShard': 0,
            'tlog': {'address': '', 'namespace': ''}
        }

    def setUp(self):
        patch('jumpscale.j.sal_zos', MagicMock()).start()
        patch('jumpscale.j.clients', MagicMock()).start()

    def tearDown(self):
        patch.stopall()

    def _test_create_minio_invalid(self, data, missing_key):
        with pytest.raises(
                ValueError, message='template should fail to instantiate if data contains no %s' % missing_key):
            minio = Minio(name="minio", data=data)
            minio.validate()

    def test_create_invalid_data(self):
        """
        Test initializing minio service with
        """
        data = {}
        keys = {
            '': 'node',
            'node': 'zerodbs',
            'zerodbs': 'namespace',
            'namespace': 'login',
            'login': 'password',
        }
        for key, missing_key in keys.items():
            data[key] = key
            self._test_create_minio_invalid(data, missing_key)

    def test_create_valid_data(self):
        minio = Minio('minio', data=self.valid_data)
        minio.validate()
        assert minio.data == self.valid_data

    def test_node_sal(self):
        """
        Test node_sal property
        """
        get_node = patch('jumpscale.j.clients.zos.get', MagicMock(return_value='node_sal')).start()
        minio = Minio('minio', data=self.valid_data)

        assert minio._node_sal == 'node_sal'
        get_node.assert_called_once_with(NODE_CLIENT)

    def test_minio_sal(self):
        """
        Test node_sal property
        """
        minio_sal = patch('jumpscale.j.sal_zos.minio.get', MagicMock(return_value='minio_sal')).start()
        minio = Minio('minio', data=self.valid_data)
        minio._get_zdbs = MagicMock()

        assert minio._minio_sal == 'minio_sal'
        assert minio_sal.called

    def test_install(self):
        """
        Test install action
        """
        minio = Minio('minio', data=self.valid_data)
        minio.api.services.find_or_create = MagicMock()
        minio._get_zdbs = MagicMock()
        minio.install()

        container_data = {
            'node': self.valid_data['node'],
            'env':  [
                {'name': 'MINIO_ACCESS_KEY', 'value': 'login'}, {'name': 'MINIO_SECRET_KEY', 'value': 'password'},
                {'name': 'AWS_ACCESS_KEY_ID', 'value': 'username'}, {'name': 'AWS_SECRET_ACCESS_KEY', 'value': 'pass'},
                {'name': 'MINIO_ZEROSTOR_META_PRIVKEY', 'value': '1234567890abcdef'}],
            'ports': ['9000:9000'],
            'nics': [{'type': 'default'}],
        }
        minio.state.check('actions', 'install', 'ok')

    def test_start(self):
        """
        Test start action
        """
        minio = Minio('minio', data=self.valid_data)
        minio.state.set('actions', 'install', 'ok')
        minio.api.services.get = MagicMock()
        minio._get_zdbs = MagicMock()
        minio.start()
        minio._minio_sal.start.assert_called_once_with()
        minio.state.check('actions', 'start', 'ok')

    def test_start_before_install(self):
        """
        Test start action without installing
        """
        with pytest.raises(StateCheckError,
                           message='start action should raise an error if minio is not installed'):
            minio = Minio('minio', data=self.valid_data)
            minio.start()

    def test_stop(self):
        """
        Test stop action
        """
        minio = Minio('minio', data=self.valid_data)
        minio.state.set('actions', 'install', 'ok')
        minio.state.delete = MagicMock()
        minio._get_zdbs = MagicMock()
        minio.stop()

        minio._minio_sal.stop.assert_called_once_with()
        minio.state.delete.call_count == 2

    def test_stop_before_install(self):
        """
        Test stop action without install
        """
        with pytest.raises(StateCheckError,
                           message='stop action should raise an error if minio is not installed'):
            minio = Minio('minio', data=self.valid_data)
            minio.stop()

    def test_uninstall(self):
        """
        Test uninstall action
        """
        minio = Minio('minio', data=self.valid_data)
        minio.state.delete = MagicMock()

        minio.uninstall()
        minio._minio_sal.destroy.assert_called_once_with()
        minio.state.delete.call_count == 2


class TestMinioHealthMonitor(TestCase):

    def setUp(self):
        self.encoder = j.data.serializers.json

    def test_hdd_failure(self):
        state = ServiceState()
        logs = [(LOG_LVL_MESSAGE_INTERNAL, self.encoder.dumps({'error': 'IO error', 'shard': '192.168.0.1:9000'}), None)]
        for level, msg, flag in logs:
            _health_monitoring(state, level, msg, flag)

        assert 'data_shards' in state.categories
        assert state.categories['data_shards']['192.168.0.1:9000'] == SERVICE_STATE_ERROR

    def test_tlog_failure(self):
        state = ServiceState()
        logs = [(LOG_LVL_MESSAGE_INTERNAL, self.encoder.dumps({'error': 'IO error', 'tlog': '192.168.0.1:9000'}), None)]
        for level, msg, flag in logs:
            _health_monitoring(state, level, msg, flag)

        assert 'tlog_shards' in state.categories
        assert state.categories['tlog_shards']['192.168.0.1:9000'] == SERVICE_STATE_ERROR

    def test_zos_failure(self):
        pass

