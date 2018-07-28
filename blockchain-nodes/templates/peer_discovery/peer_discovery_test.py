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

class TestPeerDiscoveryTemplate(TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.valid_data = {
            'node': 'node',
            'container': 'container',
            'rpcPort': 23112,
            'apiPort': 23110,
            'intervalScanNetwork': 3600,
            'intervalAddPeer': 300,
            'discoveredPeers': [],
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
        Test create discovery service
        """
        discovery = self.type(name='discovery', data=self.valid_data)
        discovery.validate()
        assert discovery.data == self.valid_data

    def test_create_with_invalid_data(self):
        """
        Test create discovery service
        """
        invalid_data = self.valid_data.copy()
        invalid_data['node'] = ''
        discovery = self.type(name='discovery', data=invalid_data)
        with self.assertRaises(ValueError):
            discovery.validate()

    def test_install(self):
        """
        Test install discovery service
        """
        discovery = self.type(name='discovery', data=self.valid_data)
        discovery.recurring_action = MagicMock()
        discovery.install()

        assert discovery.recurring_action.call_count == 2
        discovery.state.check('actions', 'install', 'ok')


        