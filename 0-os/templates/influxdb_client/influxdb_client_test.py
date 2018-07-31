from unittest.mock import MagicMock, patch
import os
import pytest
from js9 import j
from influxdb_client import InfluxdbClient
from zerorobot.template.state import StateCheckError

from JumpScale9Zrobot.test.utils import ZrobotBaseTest, mock_decorator

patch("zerorobot.template.decorator.timeout", MagicMock(return_value=mock_decorator)).start()
patch("zerorobot.template.decorator.retry", MagicMock(return_value=mock_decorator)).start()

class TestInfluxdbClientTemplate(ZrobotBaseTest):
    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), InfluxdbClient)
        cls.data = {
            'instanceName': 'main',
            'host': 'localhost',
            'port': '8086',
            'login': 'root',
            'passwd': 'root',
            'ssl': False,
            'verifySsl': False,
            }

    def setUp(self):
        self.client_get = patch('js9.j.clients', MagicMock()).start()

    def tearDown(self):
        patch.stopall()
    
    def test_install(self):
        """
        Test create new instance
        """
        stat = InfluxdbClient('influxdb_client',data=self.data)
        db = MagicMock()
        db.config = MagicMock(data=self.data)
        patch('js9.j.clients.influxdb.get', MagicMock(return_value=db)).start()
        stat.install()
        stat.state.check('actions', 'install', 'ok')
        
    def test_delete(self):
        """
        Test delete influxdb client
        """
        stat = InfluxdbClient('influxdb_client',data=self.data)
        db = MagicMock()
        db.config = MagicMock(data={})
        patch('js9.j.clients.influxdb.get', MagicMock(return_value={})).start()
        stat.delete()
        try:
            stat.state.check('actions', 'install', 'ok')
        except:
            StateCheckError