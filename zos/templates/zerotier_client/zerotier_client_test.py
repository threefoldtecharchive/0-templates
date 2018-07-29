from unittest.mock import MagicMock, patch
import os
import pytest

from zerotier_client import ZerotierClient
from JumpScale9Zrobot.test.utils import ZrobotBaseTest


class TestZerotierClientTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), ZerotierClient)

    def setUp(self):
        self.list = patch('js9.j.clients.zerotier.list', MagicMock(return_value=[])).start()
        self.get = patch('js9.j.clients.zerotier.get', MagicMock()).start()

    def tearDown(self):
        patch.stopall()

    def test_create_data_none(self):
        with pytest.raises(ValueError, message='template should fail to instantiate if data is None'):
            ZerotierClient(name="zttest", data=None)

    def test_create_data_no_token(self):
        with pytest.raises(ValueError, message="template should fail to instantiate if data doesn't contain 'token'"):
            ZerotierClient(name="zttest", data={'foo': 'bar'})

        with pytest.raises(ValueError, message="template should fail to instantiate if data doesn't contain 'token'"):
            ZerotierClient(name="zttest", data={'token': ''})

    def test_create(self):
        get = patch('js9.j.clients.zerotier.get', MagicMock()).start()
        data = {'token': 'foo'}
        ZerotierClient(name="zttest", data=data)

        self.list.assert_called_with()
        get.assert_called_with("zttest", data={'token_': data['token']})

    def test_create_already_exists(self):
        patch('js9.j.clients.zerotier.list', MagicMock(return_value=['zttest'])).start()
        ZerotierClient(name='zttest', data={'token': 'foo'})

        assert self.get.called is False

    def test_uninstall(self):
        uninstall = patch('js9.j.clients.zerotier.delete', MagicMock()).start()
        service = ZerotierClient(name='zttest', data={'token': 'foo'})
        service.uninstall()

        uninstall.assert_called_once_with('zttest')

    def test_token(self):
        service = ZerotierClient(name='zttest', data={'token': 'foo'})
        assert service.token() == 'foo'
