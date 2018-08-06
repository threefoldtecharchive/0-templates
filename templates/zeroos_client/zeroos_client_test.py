from unittest.mock import MagicMock, patch
import os

import pytest

from zeroos_client import ZeroosClient

from JumpscaleZrobot.test.utils import ZrobotBaseTest


class TestZeroosClientTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), ZeroosClient)
        cls.valid_data = {
            'password': 'password',
            'timeout': 120,
            'ssl': False,
            'db': 0,
            'port': 6379,
            'host': '127.0.0.1',
            'unixSocket': '',
        }

    def setUp(self):
        self.list = patch('jumpscale.j.clients.zos.list', MagicMock(return_value=[])).start()
        self.get = patch('jumpscale.j.clients.zos.get', MagicMock()).start()

    def tearDown(self):
        patch.stopall()

    def test_create_invalid_data(self):
        with pytest.raises(
                ValueError, message='template should fail to instantiate if neither host nor unixSocket are supplied'):
            ZeroosClient(name="zos", data={'host': '', 'unixSocket': '', 'port': ''})

    def test_create(self):
        get = patch('jumpscale.j.clients.zos.get', MagicMock()).start()
        ZeroosClient(name="zos", data=self.valid_data)
        client_data = {
            'host': self.valid_data['host'],
            'port': self.valid_data['port'],
            'password_': self.valid_data['password'],
            'ssl': self.valid_data['ssl'],
            'db': self.valid_data['db'],
            'timeout': self.valid_data['timeout'],
            'unixsocket': self.valid_data['unixSocket'],
        }

        self.list.assert_called_with()
        get.assert_called_with("zos", data=client_data)

    def test_create_already_exists(self):
        patch('jumpscale.j.clients.zos.list', MagicMock(return_value=['zos'])).start()
        ZeroosClient(name='zos', data=self.valid_data)

        assert self.get.called is False

    def test_delete(self):
        delete = patch('jumpscale.j.clients.zos.delete', MagicMock()).start()
        service = ZeroosClient(name='zos', data=self.valid_data)
        service.delete()

        delete.assert_called_once_with('zos')
