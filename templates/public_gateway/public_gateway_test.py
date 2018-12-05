from unittest.mock import MagicMock, patch
import pytest
import os
import copy
import netaddr

from public_gateway import PublicGateway
from JumpscaleZrobot.test.utils import ZrobotBaseTest

class AlwaysTrue:
    def __eq__(self, other):
        return True


class TestPublicGatewayTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), PublicGateway)

    def setUp(self):
        self.valid_data = {
                'portforwards': [{'srcport': 34022, 'dstip': '192.168.1.1', 'dstport': 22, 'name': 'ssh'}],
                'httpproxies': [{'name': 'httpproxy', 'host': 'myhost.com', 'destinations': ['http://192.168.1.1:8000']}]
        }
        patch('jumpscale.j.sal_zos', MagicMock()).start()
        self.service, self.gwservice = self._mock_service(self.valid_data)

    def tearDown(self):
        patch.stopall()

    def test_install(self):
        self.service.install()
        assert self.gwservice.schedule_action.call_count == 2

    def test_info(self):
        info = self.service.info()
        self.gwservice.schedule_action.assert_called_once_with('info')
        assert info['portforwards'] == self.valid_data['portforwards']
        assert info['httpproxies'] == self.valid_data['httpproxies']

    def list_name_contains(self, datalist, name):
        for item in datalist:
            if item['name'] == name:
                return True
        return False

    def _mock_service(self, data, mockget=True, mockfind=True):
        service = PublicGateway(name='service', data=data)
        gwservice = MagicMock()
        if mockget:
            service.api.services.get = MagicMock(return_value=gwservice)
        if mockfind:
            service.api.services.find = MagicMock(return_value=[gwservice])
        return service, gwservice

    def test_validate_data(self):
        data = copy.deepcopy(self.valid_data)
        service, gwservice = self._mock_service(data)
        service.validate()
        with pytest.raises(RuntimeError, message='Gateway service missing'):
            service, gwservice = self._mock_service(data, mockfind=False)
            service.validate()

        with pytest.raises(ValueError, message='Portforward withouth name'):
            data = copy.deepcopy(self.valid_data)
            data['portforwards'][0].pop('name')
            service, gwservice = self._mock_service(data)
            service.validate()

        with pytest.raises(ValueError, message='Portforward with invalid srcport'):
            data = copy.deepcopy(self.valid_data)
            data['portforwards'][0]['srcport'] = '233'
            service, gwservice = self._mock_service(data)
            service.validate()

        with pytest.raises(ValueError, message='Portforward with invalid dstport'):
            data = copy.deepcopy(self.valid_data)
            data['portforwards'][0]['dstport'] = '233'
            service, gwservice = self._mock_service(data)
            service.validate()

        with pytest.raises(netaddr.AddrFormatError, message='Portforward with invalid dstip'):
            data = copy.deepcopy(self.valid_data)
            data['portforwards'][0]['dstip'] = 'gdfgdf'
            service, gwservice = self._mock_service(data)
            service.validate()

        with pytest.raises(ValueError, message='HTTP Proxy with missing name'):
            data = copy.deepcopy(self.valid_data)
            data['httpproxies'][0].pop('name')
            service, gwservice = self._mock_service(data)
            service.validate()

        with pytest.raises(ValueError, message='HTTP Proxy with missing host'):
            data = copy.deepcopy(self.valid_data)
            data['httpproxies'][0].pop('host')
            service, gwservice = self._mock_service(data)
            service.validate()

        with pytest.raises(ValueError, message='HTTP Proxy with missing destinations'):
            data = copy.deepcopy(self.valid_data)
            data['httpproxies'][0].pop('destinations')
            service, gwservice = self._mock_service(data)
            service.validate()


    def test_add_proxy(self):
        proxy = {'name': 'myproxy', 'host': 'example.com', 'destinations': ['http://192.168.1.1:8080']}
        self.service.add_http_proxy(proxy)
        self.gwservice.schedule_action.assert_called_once_with('add_http_proxy', args=AlwaysTrue())
        assert self.list_name_contains(self.service.data['httpproxies'], 'myproxy')

    def test_remove_proxy(self):
        self.test_add_proxy()
        self.service.remove_http_proxy('myproxy')
        self.gwservice.schedule_action.assert_called_with('remove_http_proxy', args=AlwaysTrue())
        assert not self.list_name_contains(self.service.data['httpproxies'], 'myproxy')

    def test_add_portforward(self):
        fwd = {'name': 'forward', 'srcport': 34, 'dstip': '192.168.1.228', 'dstport': 80}
        self.service.add_portforward(fwd)
        self.gwservice.schedule_action.assert_called_once_with('add_portforward', args=AlwaysTrue())
        assert self.list_name_contains(self.service.data['portforwards'], 'forward')

    def test_remove_forward(self):
        self.test_add_portforward()
        self.service.remove_portforward('forward')
        self.gwservice.schedule_action.assert_called_with('remove_portforward', args=AlwaysTrue())
        assert not self.list_name_contains(self.service.data['portforwards'], 'forward')

