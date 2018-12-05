from unittest.mock import MagicMock, patch
import os

import pytest

from erp_registeration import ErpRegisteration
from Jumpscale import j

from JumpscaleZrobot.test.utils import ZrobotBaseTest


class TestErpRegisterationTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), ErpRegisteration)
        cls.valid_data = {
            'url': 'url',
            'db': 'db',
            'username': 'username',
            'password': 'password',
            'productId': 'productId',
            'botToken': 'botToken',
            'chatId': 'chatId'
        }

    def tearDown(self):
        patch.stopall()

    def _test_create_erp_invalid(self, data, missing_key):
        with pytest.raises(
                ValueError, message='template should fail to instantiate if data dict is missing the %s' % missing_key):
            erp = ErpRegisteration(name='erp', data=data)
            erp.validate()

    def test_invalid_data(self):
        """
        Test create with invalid data
        :return:
        """
        data = {}
        # sequentially add expected data and verify that the validation raises an error for missing keys
        keys = {
            '': 'url',
            'url': 'db',
            'db': 'username',
            'username': 'password',
            'password': 'productId',
            'productId': 'botToken',
            'botToken': 'chatId'
        }

        for key, missing_key in keys.items():
            data[key] = key
            self._test_create_erp_invalid(data, missing_key)

    def test_create_valid_data(self):
        """
        Test create ErpRegisteration with valid data
        """
        erp = ErpRegisteration(name='erp', data=self.valid_data)
        erp.validate()
        assert erp.data == self.valid_data

    def test_get_erp_client(self):
        """
        Test _get_erp_client
        """
        client_get = patch('jumpscale.j.clients.erppeek.get', MagicMock()).start()
        erp = ErpRegisteration(name='erp', data=self.valid_data)
        erp._get_erp_client()
        data = {
            'url': erp.data['url'],
            'db': erp.data['db'],
            'password_': erp.data['password'],
            'username': erp.data['username'],
        }
        client_get.assert_called_with(instance=erp.guid, data=data, create=True, die=True)

    def test_get_bot_client(self):
        """
        Test _get_bot_client
        :return:
        """
        client_get = patch('jumpscale.j.clients.telegram_bot.get', MagicMock()).start()
        erp = ErpRegisteration(name='erp', data=self.valid_data)
        erp._get_bot_client()
        data = {
            'bot_token_': erp.data['botToken'],
        }
        client_get.assert_called_with(instance=erp.guid, data=data, create=True, die=True)

    def test_register_new_node(self):
        """
        Test register new node
        """
        erp = ErpRegisteration(name='erp', data=self.valid_data)
        client = MagicMock()
        client.count_records = MagicMock(return_value=0)
        erp._get_erp_client = MagicMock(return_value=client)
        erp._get_bot_client = MagicMock()
        erp.register('node')

        client.create_record.assert_called_once_with('stock.production.lot',
                                                     {'name': 'node', 'product_id': erp.data['productId']})
        assert erp._get_erp_client.called
        assert erp._get_bot_client.called

    def test_register_old_node(self):
        """
        Test register old node
        """
        erp = ErpRegisteration(name='erp', data=self.valid_data)
        client = MagicMock()
        client.count_records = MagicMock(return_value=1)
        erp._get_erp_client = MagicMock(return_value=client)
        erp._get_bot_client = MagicMock()
        erp.register('node')

        client.create_record.assert_not_called()
        assert erp._get_erp_client.called
        assert erp._get_bot_client.called

    def test_registeration_error(self):
        """
        Test error during registeration
        """
        with pytest.raises(j.exceptions.RuntimeError, message='action should fail if an error was raised'):
            erp = ErpRegisteration(name='erp', data=self.valid_data)
            erp._get_erp_client = MagicMock(side_effect=Exception)
            erp._get_bot_client = MagicMock()
            erp.register('node')

