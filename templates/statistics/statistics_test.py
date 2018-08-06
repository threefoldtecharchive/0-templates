from unittest.mock import MagicMock, patch
import os

import pytest
from jumpscale import j
from statistics import Statistics
from zerorobot.template.state import StateCheckError

from JumpScale9Zrobot.test.utils import ZrobotBaseTest, mock_decorator

patch("zerorobot.template.decorator.timeout", MagicMock(return_value=mock_decorator)).start()
patch("zerorobot.template.decorator.retry", MagicMock(return_value=mock_decorator)).start()

class TestStatisticsTemplate(ZrobotBaseTest):
    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), Statistics)
        cls.data = {
            'influxdbClient': 'influxdb_test'
        }

    def setUp(self):
        self.client_get = patch('js9.j.clients', MagicMock()).start()

    def tearDown(self):
        patch.stopall()

    def test_install_with_database(self):
        """
        Test statistics start with database exist
        """
        stat = Statistics('statistic',data=self.data)
        db = MagicMock()
        db.config = MagicMock(data={'database': 'statistics'})
        patch('js9.j.clients.influxdb.get', MagicMock(return_value=db)).start()
        stat.install()
        stat.state.check('actions', 'install', 'ok')
        db.create_database.assert_not_called()
        db.switch_database.assert_not_called()
    
    def test_install_without_database(self):
        """
        Test statistics start with create new database
        """
        stat = Statistics('statistic',data=self.data)
        db = MagicMock()
        db.config = MagicMock(data={'database': 'Test'})
        patch('js9.j.clients.influxdb.get', MagicMock(return_value=db)).start()
        stat.install()
        stat.state.check('actions', 'install', 'ok')
        db.create_database.assert_called_once_with('statistics')
        db.switch_database.assert_called_once_with('statistics')
        
    def test_uninstall(self):
        """
        Test statistics stop
        """
        stat = Statistics('statistic',data=self.data)
        stat.uninstall()
        try:
            stat.state.check('actions', 'install', 'ok')
        except:
            StateCheckError