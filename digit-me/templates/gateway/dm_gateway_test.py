import copy
import os
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest
from requests import HTTPError

from gateway import PUBLIC_GW_ROBOTS, Gateway
from js9 import j
from JumpScale9Zrobot.test.utils import ZrobotBaseTest

PRIVATEZT = '1234567890123456'
NODEID = 'aabbcceeff'


class AlwaysTrue:
    def __eq__(self, other):
        return True


class TestGatewayTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), Gateway)

    def setUp(self):
        self.valid_data = {
            'status': 'halted',
            'hostname': 'hostname',
            'networks': [],
            'nodeId': NODEID,
            'portforwards': [],
            'httpproxies': [],
            'domain': 'domain',
        }
        patch('js9.j.clients', MagicMock()).start()

    def tearDown(self):
        patch.stopall()

    def _mock_service(self, data, mock_capacity=True):
        self.service = Gateway(name='service', data=data)
        self.robotapi = MagicMock()
        self.vmservice = MagicMock()
        self.service.api.services.get = MagicMock(return_value=self.vmservice)
        self.publibcrobotapi = MagicMock()
        self.gateway = MagicMock()
        self.public_gateway = MagicMock()
        self.robotapi.services.get.return_value = self.gateway
        self.robotapi.services.find_or_create.return_value = self.gateway
        self.publibcrobotapi.services.get.return_value = self.public_gateway
        self.publibcrobotapi.services.find_or_create.return_value = self.public_gateway
        kwargs = {NODEID: self.robotapi}
        for url in PUBLIC_GW_ROBOTS:
            key = urlparse(url).netloc
            kwargs[key] = self.publibcrobotapi
        j.clients.zrobot.robots = kwargs
        capacity = MagicMock()
        self.mocknode = MagicMock(robot_address='url')
        capacity.api.GetCapacity.return_value = (self.mocknode, None)
        j.clients.grid_capacity.get.return_value = capacity

        # public gateay info
        self.public_gateway_info = {'httpproxies': [], 'zerotierId': 'abcdef1234567890'}
        self.public_gateway.schedule_action.return_value.wait.return_value.result = self.public_gateway_info

        # gateway network
        self.gateway_info = {
            'networks': [{
                'public': True,
                'config': {'cidr': '172.18.0.1/16'}
            }],
            'portforwards': []
        }

        self.gateway.schedule_action.return_value.wait.return_value.result = self.gateway_info
        # vm info
        self.vmservice.schedule_action.return_value.wait.return_value.result = {
            'zerotier': {'id': PRIVATEZT, 'ztClient': 'main', },
            'ztIdentity': 'abcdef:423423'
        }

    def test_create_valid_data(self):
        data = copy.deepcopy(self.valid_data)
        self._mock_service(data)
        self.service.validate()
        self.service.data.pop('publicGatewayRobot', None)
        assert self.service.data == self.valid_data

    def test_create_invalid_data(self):
        data = copy.deepcopy(self.valid_data)
        data['nodeId'] = '112233445566'
        self._mock_service(data)

        capacity = MagicMock()
        capacity.api.GetCapacity.side_effect = RuntimeError()
        j.clients.grid_capacity.get.return_value = capacity

        self.mocknode.clear()
        with pytest.raises(RuntimeError, message='Node should not be found'):
            self.service.validate()

    def test_get_info(self):
        data = copy.deepcopy(self.valid_data)
        self._mock_service(data)
        self.service.validate()
        data = self.service._get_info(None, None)
        assert data['ztip'] == '172.18.0.1'
        assert data['gwservice'] == self.gateway
        assert data['pgwservice'] == self.public_gateway

    def test_install(self):
        """
        Test install action
        """
        data = copy.deepcopy(self.valid_data)
        self._mock_service(data)
        self.service.validate()
        self.service.install()
        self.gateway.schedule_action.assert_any_call('install')

    def test_add_portforward(self):
        """
        Test add_portforward action
        """
        data = copy.deepcopy(self.valid_data)
        data['networks'] = [{'name': 'network', 'type': 'zerotier', 'id': PRIVATEZT}]
        self._mock_service(data)
        self.service.validate()
        portforward = {'name': 'pf', 'vm': 'myvm', 'dstport': 22, 'srcport': 22, 'protocols': ['tcp']}
        self.service.add_portforward(portforward)
        assert self.service.data['portforwards'] == [portforward]
        self.gateway.schedule_action.assert_any_call('add_portforward', args=AlwaysTrue())
        self.public_gateway.schedule_action.assert_any_call('add_portforward', args=AlwaysTrue())

    def list_name_contains(self, datalist, name):
        for item in datalist:
            if item['name'] == name:
                return True
        return False

    def test_remove_portforward(self):
        self.test_add_portforward()
        self.gateway_info['portforwards'].append({'name': 'forward_pf'})
        self.service.remove_portforward('pf')
        assert not self.list_name_contains(self.service.data['portforwards'], 'pf')
        self.gateway.schedule_action.assert_any_call('remove_portforward', args={'name': 'forward_pf'})
        self.public_gateway.schedule_action.assert_any_call('remove_portforward', args={'name': 'pf'})

    def test_add_proxy(self):
        data = copy.deepcopy(self.valid_data)
        data['networks'] = [{'name': 'network', 'type': 'zerotier', 'id': PRIVATEZT}]
        self._mock_service(data)
        self.service.validate()
        proxy = {'name': 'myproxy', 'destinations': [{'vm': 'myvm', 'port': 8282}], 'host': '172.19.0.1', 'types': ['http']}
        self.service.add_http_proxy(proxy)
        assert self.service.data['httpproxies'] == [proxy]
        self.public_gateway.schedule_action.assert_any_call('add_http_proxy', args=AlwaysTrue())
        self.gateway.schedule_action.assert_any_call('add_portforward', args=AlwaysTrue())

    def test_remove_proxy(self):
        self.test_add_proxy()
        self.public_gateway_info['httpproxies'].append({'name': 'myproxy'})
        self.gateway_info['portforwards'].append({'name': 'proxy_myproxy_myvm'})
        self.service.remove_http_proxy('myproxy')
        assert not self.list_name_contains(self.service.data['httpproxies'], 'myproxy')
        self.public_gateway.schedule_action.assert_any_call('remove_http_proxy', args={'name': 'myproxy'})
        self.gateway.schedule_action.assert_any_call('remove_portforward', args=AlwaysTrue())
