from unittest.mock import MagicMock, patch, call
import copy
import os
import pytest


from gateway import Gateway, NODE_CLIENT
from zerorobot.template.state import StateCheckError

from JumpscaleZrobot.test.utils import ZrobotBaseTest


class TestGatewayTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), Gateway)

    def setUp(self):
        self.valid_data = {
            'status': 'halted',
            'hostname': 'hostname',
            'networks': [],
            'portforwards': [],
            'httpproxies': [],
            'domain': 'domain',
            'certificates': [],
            'ztIdentity': '',
        }
        patch('jumpscale.j.clients', MagicMock()).start()

    def tearDown(self):
        patch.stopall()

    def test_create_valid_data(self):
        gw = Gateway('gw', data=self.valid_data)
        gw.validate()
        assert gw.data == self.valid_data

    def test_node_sal(self):
        """
        Test _node_sal property
        """
        get_node = patch('jumpscale.j.clients.zos.get', MagicMock(return_value='node_sal')).start()
        gw = Gateway('gw', data=self.valid_data)

        assert gw._node_sal == 'node_sal'
        get_node.assert_called_once_with(NODE_CLIENT)

    def test_gateway_sal(self):
        """
        Test _gateway_sal property
        """
        gw = Gateway('gw', data=self.valid_data)
        gw_sal = MagicMock()
        gw._node_sal.primitives.from_dict.return_value = gw_sal

        assert gw._gateway_sal == gw_sal
        gw._node_sal.primitives.from_dict.assert_called_once_with('gateway', self.valid_data)

    def test_install(self):
        """
        Test install action
        """
        gw = Gateway('gw', data=self.valid_data)
        gw_sal = MagicMock(zt_identity='zt_identity')
        gw._node_sal.primitives.from_dict.return_value = gw_sal
        gw.install()
        gw_sal.deploy.assert_called_once_with()
        assert gw.data['ztIdentity'] == 'zt_identity'
        gw.state.check('actions', 'install', 'ok')
        gw.state.check('actions', 'start', 'ok')

    def test_add_portforward(self):
        """
        Test add_portforward action
        """
        self.valid_data['networks'] = [{'name': 'network'}]
        gw = Gateway('gw', data=self.valid_data)
        gw.state.set('actions', 'start', 'ok')
        portforward = {'name': 'pf', 'dstip': '196.23.12.42', 'dstport': 22, 'srcnetwork': 'network', 'srcport': 22, 'protocols': ['tcp']}
        gw.add_portforward(portforward)
        gw._gateway_sal.configure_fw.assert_called_once_with()
        assert gw.data['portforwards'] == [portforward]

    def test_add_portforward_exception(self):
        """
        Test add_portforward action raises exception
        """
        with pytest.raises(RuntimeError,
                           message='action should raise an error if configure_fw raises an exception'):
            self.valid_data['networks'] = [{'name': 'network'}]
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            gw._gateway_sal.configure_fw.side_effect = RuntimeError
            portforward = {'name': 'pf', 'dstip': '196.23.12.42', 'dstport': 22, 'srcnetwork': 'network', 'srcport': 22, 'protocols': ['tcp']}
            gw.add_portforward(portforward)
            assert gw._gateway_sal.configure_fw.call_count == 2
            assert gw.data['portforwards'] == []

    def test_add_portforward_network_doesnt_exist(self):
        """
        Test add_portforward action using a network that doesn't exist
        """
        with pytest.raises(LookupError,
                           message='action should raise an error if srcnetwork doesn\'t exist'):
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            portforward = {'name': 'pf', 'dstip': '196.23.12.42', 'dstport': 22, 'srcnetwork': 'network', 'srcport': 22, 'protocols': ['tcp']}
            gw.add_portforward(portforward)

    def test_add_portforward_before_start(self):
        """
        Test add_portforward action before gateway start
        """
        with pytest.raises(StateCheckError,
                           message='action should raise an error if gateway isn\'t started'):
            self.valid_data['networks'] = [{'name': 'network'}]
            gw = Gateway('gw', data=self.valid_data)
            portforward = {'name': 'pf', 'dstip': '196.23.12.42', 'dstport': 22, 'srcnetwork': 'network', 'srcport': 22, 'protocols': ['tcp']}
            gw.add_portforward(portforward)

    def test_add_portforward_name_exists(self):
        """
        Test add_portforward action when another portforward with the same name exists
        """
        with pytest.raises(ValueError,
                           message='action should raise an error if another portforward with the same name exist'):
            self.valid_data['portforwards'] = [{'name': 'pf', 'dstip': '196.23.12.42', 'dstport': 21, 'srcnetwork': 'network', 'srcport': 21, 'protocols': ['tcp']}]
            self.valid_data['networks'] = [{'name': 'network'}]
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            portforward = {'name': 'pf', 'dstip': '196.23.12.42', 'dstport': 22, 'srcnetwork': 'network', 'srcport': 22, 'protocols': ['tcp']}
            gw.add_portforward(portforward)

    def test_add_portforward_combination_exists_same_protocols(self):
        """
        Test add_portforward action when another portforward with the same srcnetwork and srcport exists and have the same protocols
        """
        with pytest.raises(ValueError,
                           message='action should raise an error if another portforward with the same name exist'):
            self.valid_data['portforwards'] = [{'name': 'pf2', 'dstip': '196.23.12.42', 'dstport': 22, 'srcnetwork': 'network', 'srcport': 22, 'protocols': ['tcp']}]
            self.valid_data['networks'] = [{'name': 'network'}]
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            portforward = {'name': 'pf', 'dstip': '196.23.12.42', 'dstport': 22, 'srcnetwork': 'network', 'srcport': 22, 'protocols': ['tcp']}
            gw.add_portforward(portforward)

    def test_add_portforward_combination_exists_different_protocols(self):
        """
        Test add_portforward action when another portforward with the same srcnetwork and srcport exists and have different protocols
        """
        portforward_one = {'name': 'pf2', 'dstip': '196.23.12.42', 'dstport': 22, 'srcnetwork': 'network', 'srcport': 22, 'protocols': ['udp']}
        self.valid_data['portforwards'] = [portforward_one]
        self.valid_data['networks'] = [{'name': 'network'}]
        gw = Gateway('gw', data=self.valid_data)
        gw.state.set('actions', 'start', 'ok')
        portforward_two = {'name': 'pf', 'dstip': '196.23.12.42', 'dstport': 22, 'srcnetwork': 'network', 'srcport': 22, 'protocols': ['tcp']}
        gw.add_portforward(portforward_two)
        assert gw.data['portforwards'] == [portforward_one, portforward_two]

    def test_remove_portforward(self):
        """
        Test remove_portforward action
        """
        self.valid_data['portforwards'] = [{'name': 'pf', 'dstip': '196.23.12.42', 'dstport': 21, 'srcnetwork': 'network', 'srcport': 21, 'protocols': ['tcp']}]
        gw = Gateway('gw', data=self.valid_data)
        gw.state.set('actions', 'start', 'ok')
        gw.remove_portforward('pf')
        assert gw.data['portforwards'] == []

    def test_remove_portforward_exception(self):
        """
        Test remove_portforward action raises exception
        """
        with pytest.raises(RuntimeError,
                           message='action should raise an error if configure_fw raises an exception'):
            forwards = [{'name': 'pf', 'dstip': '196.23.12.42', 'dstport': 21, 'srcnetwork': 'network', 'srcport': 21, 'protocols': ['tcp']}]
            self.valid_data['portforwards'] = forwards
            gw = Gateway('gw', data=self.valid_data)
            gw._gateway_sal.configure_fw.side_effect = RuntimeError
            gw.state.set('actions', 'start', 'ok')
            gw.remove_portforward('pf')
            assert gw._gateway_sal.configure_fw.call_count == 2
            assert gw.data['portforwards'] == forwards

    def test_remove_portforward_before_start(self):
        """
        Test remove_portforward action before gateway start
        """
        with pytest.raises(StateCheckError,
                           message='action should raise an error if gateway isn\'t started'):
            self.valid_data['portforwards'] = [{'name': 'pf', 'dstip': '196.23.12.42', 'dstport': 21, 'srcnetwork': 'network', 'srcport': 21, 'protocols': ['tcp']}]
            gw = Gateway('gw', data=self.valid_data)
            gw.remove_portforward('pf')

    def test_remove_portforward_doesnt_exist(self):
        """
        Test remove_portforward action if the portforward doesn't exist
        """
        gw = Gateway('gw', data=self.valid_data)
        gw.state.set('actions', 'start', 'ok')
        gw.remove_portforward('pf')

    def test_add_http_proxy(self):
        """
        Test add_http_proxy action
        """
        gw = Gateway('gw', data=self.valid_data)
        gw.state.set('actions', 'start', 'ok')
        proxy = {'host': 'host', 'destinations': ['destination'],  'types': ['http'], 'name': 'proxy'}
        gw.add_http_proxy(proxy)
        assert gw.data['httpproxies'] == [proxy]
        gw._gateway_sal.configure_http.assert_called_once_with()

    def test_add_http_proxy_exception(self):
        """
        Test add_http_proxy action raises exception
        """
        with pytest.raises(RuntimeError,
                           message='action should raise an error if configure_http raises an exception'):
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            proxy = {'host': 'host', 'destinations': ['destination'],  'types': ['http'], 'name': 'proxy'}
            gw._gateway_sal.configure_http.side_effect = RuntimeError
            gw.add_http_proxy(proxy)
            assert gw.data['httpproxies'] == []
            assert gw._gateway_sal.configure_http.call_count == 2

    def test_add_http_proxy_before_start(self):
        """
        Test add_http_proxy action before gateway start
        """
        with pytest.raises(StateCheckError, message='actions should raise an error if gateway isn\'t started'):
            gw = Gateway('gw', data=self.valid_data)
            proxy = {'host': 'host', 'destinations': ['destination'],  'types': ['http'], 'name': 'proxy'}
            gw.add_http_proxy(proxy)

    def test_add_http_proxy_name_exists(self):
        """
        Test add_http_proxy action if another proxy with the same name exists
        """
        with pytest.raises(ValueError,
                           message='action should raise an error if another http proxy with the same name exist'):
            proxy = {'host': 'host', 'destinations': ['destination'],  'types': ['http'], 'name': 'proxy'}
            proxy2 = {'host': 'host2', 'destinations': ['destination'],  'types': ['http'], 'name': 'proxy'}
            self.valid_data['httpproxies'].append(proxy)
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            gw.add_http_proxy(proxy2)

    def test_add_http_proxy_host_exists(self):
        """
        Test add_http_proxy action if another proxy has the same host
        """
        with pytest.raises(ValueError,
                   message='action should raise an error if another http proxy with the same host exist'):
            proxy = {'host': 'host', 'destinations': ['destination'],  'types': ['http'], 'name': 'proxy'}
            proxy2 = {'host': 'host', 'destinations': ['destination'],  'types': ['http'], 'name': 'proxy2'}
            self.valid_data['httpproxies'].append(proxy)
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            gw.add_http_proxy(proxy2)

    def test_remove_http_proxy(self):
        """
        Test remove_http_proxy action
        """
        self.valid_data['httpproxies'] = [{'host': 'host', 'destinations': ['destination'], 'types': ['http'], 'name': 'proxy'}]
        gw = Gateway('gw', data=self.valid_data)
        gw.state.set('actions', 'start', 'ok')
        gw.remove_http_proxy('proxy')
        assert gw.data['httpproxies'] == []
        gw._gateway_sal.configure_http.assert_called_once_with()

    def test_remove_http_proxy_exception(self):
        """
        Test remove_http_proxy action
        """
        with pytest.raises(RuntimeError,
                           message='action should raise an error if configure_http raises an exception'):
            proxies = [{'host': 'host', 'destinations': ['destination'], 'types': ['http'], 'name': 'proxy'}]
            self.valid_data['httpproxies'] = proxies
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            gw._gateway_sal.configure_http.side_effect = RuntimeError
            gw.remove_http_proxy('proxy')
            assert gw.data['httpproxies'] == proxies
            assert gw._gateway_sal.configure_http.call_count == 2

    def test_remove_http_proxy_before_start(self):
        """
        Test remove_http_proxy action before gateway is started
        """

        with pytest.raises(StateCheckError, message='actions should raise an error if gateway isn\'t started'):
            self.valid_data['httpproxies'] = [{'host': 'host', 'destinations': ['destination'], 'types': ['http'], 'name': 'proxy'}]
            gw = Gateway('gw', data=self.valid_data)
            gw.remove_http_proxy('proxy')

    def test_remove_http_proxy_doesnt_exist(self):
        """
        Test remove_http_proxy action if proxy doesn't exist
        """
        gw = Gateway('gw', data=self.valid_data)
        gw.state.set('actions', 'start', 'ok')
        gw.remove_http_proxy('proxy')

    def test_add_dhcp_host(self):
        """
        Test add_dhcp_host action
        """
        self.valid_data['networks'] = [{'name': 'network', 'dhcpserver': {'hosts': [{'macaddress': 'address1'}]}}]
        gw = Gateway('gw', data=self.valid_data)
        gw.state.set('actions', 'start', 'ok')
        gw.add_dhcp_host('network', {'macaddress': 'address2'})
        assert gw.data['networks'] == [{'name': 'network', 'dhcpserver': {'hosts': [{'macaddress': 'address1'}, {'macaddress': 'address2'}]}}]
        gw._gateway_sal.configure_dhcp.assert_called_once_with()
        gw._gateway_sal.configure_cloudinit.assert_called_once_with()

    def test_add_dhcp_host_exception(self):
        """
        Test add_dhcp_host action raises exception
        """
        with pytest.raises(RuntimeError,
                           message='action should raise an error if configure_dhcp raises an exception'):
            self.valid_data['networks'] = [{'name': 'network', 'dhcpserver': {'hosts': [{'macaddress': 'address1'}]}}]
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            gw._gateway_sal.configure_dhcp.side_effect = RuntimeError
            gw.add_dhcp_host('network', {'macaddress': 'address2'})
            assert gw.data['networks'] == []
            assert gw._gateway_sal.configure_dhcp.call_count == 2
            assert gw._gateway_sal.configure_cloudinit.call_count == 2

    def test_add_dhcp_host_before_start(self):
        """
        Test add_dhcp_host action before gateway start
        """
        with pytest.raises(StateCheckError, message='actions should raise an error if gateway isn\'t started'):
            self.valid_data['networks'] = [{'name': 'network', 'dhcpserver': {'hosts': [{'macaddress': 'address1'}]}}]
            gw = Gateway('gw', data=self.valid_data)
            gw.add_dhcp_host('network', {'macaddress': 'address2'})

    def test_add_dhcp_host_name_doesnt_exists(self):
        """
        Test add_dhcp_host action if network with name doesnt exist
        """
        with pytest.raises(LookupError,
                           message='action should raise an error if network with this name doesnt exist'):
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            gw.add_dhcp_host('network', {'macaddress': 'address2'})

    def test_add_http_proxy_macaddress_exists(self):
        """
        Test add_dhcp_host action if host with the same macaddress exists
        """
        with pytest.raises(ValueError,
                           message='action should raise an error if another host with the same macaddress exists'):
            self.valid_data['networks'] = [{'name': 'network', 'dhcpserver': {'hosts': [{'macaddress': 'address1'}]}}]
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            gw.add_dhcp_host('network', {'macaddress': 'address1'})

    def test_remove_dhcp_host(self):
        """
        Test remove_dhcp_host action
        """
        self.valid_data['networks'] = [{'name': 'network', 'dhcpserver': {'hosts': [{'macaddress': 'address1'}]}}]
        gw = Gateway('gw', data=self.valid_data)
        gw.state.set('actions', 'start', 'ok')
        gw.remove_dhcp_host('network', {'macaddress': 'address1'})
        assert gw.data['networks'] == [{'name': 'network', 'dhcpserver': {'hosts': []}}]
        gw._gateway_sal.configure_dhcp.assert_called_once_with()
        gw._gateway_sal.configure_cloudinit.assert_called_once_with()

    def test_remove_dhcp_host_exception(self):
        """
        Test remove_dhcp_host action raises exception
        """
        with pytest.raises(RuntimeError,
                           message='action should raise an error if configure_dhcp raises an exception'):
            networks = [{'name': 'network', 'dhcpserver': {'hosts': [{'macaddress': 'address1'}]}}]
            self.valid_data['networks'] = networks
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            gw._gateway_sal.configure_dhcp.side_effect = RuntimeError
            gw.remove_dhcp_host('network', {'macaddress': 'address1'})
            assert gw.data['networks'] == networks
            assert gw._gateway_sal.configure_dhcp.call_count == 2
            assert gw._gateway_sal.configure_cloudinit.call_count == 2

    def test_remove_dhcp_host_before_start(self):
        """
        Test remove_dhcp_host action before gateway start
        """
        with pytest.raises(StateCheckError, message='actions should raise an error if gateway isn\'t started'):
            self.valid_data['networks'] = [{'name': 'network', 'dhcpserver': {'hosts': [{'macaddress': 'address1'}]}}]
            gw = Gateway('gw', data=self.valid_data)
            gw.remove_dhcp_host('network', {'macaddress': 'address1'})

    def test_remove_dhcp_host_name_doesnt_exists(self):
        """
        Test remove_dhcp_host action if network with name doesnt exist
        """
        with pytest.raises(LookupError,
                   message='action should raise an error if network with this name doesnt exist'):
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            gw.remove_dhcp_host('network', {'macaddress': 'address2'})

    def test_remove_dhcp_host_macaddress_doesnt_exists(self):
        """
        Test remove_dhcp_host action if host with the same macaddress doesnt exist
        """
        with pytest.raises(LookupError,
                           message='action should raise an error if host with the macaddress doesnt exist'):
            self.valid_data['networks'] = [{'name': 'network', 'dhcpserver': {'hosts': [{'macaddress': 'address1'}]}}]
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            gw.remove_dhcp_host('network', {'macaddress': 'address2'})

    def test_start(self):
        """
        Test start action
        """
        gw = Gateway('gw', data=self.valid_data)
        gw.state.set('actions', 'install', 'ok')
        gw.install = MagicMock()
        gw.start()
        gw.install.assert_called_once_with()

    def test_start_not_installed(self):
        """
        Test start action, gateway isnt installed
        """
        with pytest.raises(StateCheckError, message='actions should raise an error if gateway isn\'t installed'):
            gw = Gateway('gw', data=self.valid_data)
            gw.start()

    def test_add_network(self):
        """
        Test add_network action
        """
        network = {'name': 'network', 'type': 'default', 'id': 'id'}
        gw = Gateway('gw', data=self.valid_data)
        gw.state.set('actions', 'start', 'ok')
        gw.add_network(network)
        assert gw.data['networks'] == [network]
        gw._gateway_sal.deploy.assert_called_once_with()

    def test_add_network_exception(self):
        """
        Test add_network action raises exception
        """
        with pytest.raises(RuntimeError, message='actions should raise an error deploy raises an exception'):
            network = {'name': 'network', 'type': 'default', 'id': 'id'}
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            gw._gateway_sal.deploy.side_effect = RuntimeError
            gw.add_network(network)
            assert gw.data['networks'] == []
            assert gw._gateway_sal.deploy.call_count == 2

    def test_add_network_name_exist(self):
        """
        Test add_network action if network with another name exists
        """
        with pytest.raises(ValueError,
                           message='action should raise an error if another network with the same name'):
            network = {'name': 'network', 'type': 'default', 'id': 'id'}
            network_two = {'name': 'network', 'type': 'default', 'id': 'id2'}
            self.valid_data['networks'].append(network)
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            gw.add_network(network_two)

    def test_add_network_name_exist_same_combination(self):
        """
        Test add_network action if network with the same type and id combination exists
        """
        with pytest.raises(ValueError,
                           message='action should raise an error if another network with the same type and id combination exists'):
            network = {'name': 'network', 'type': 'default', 'id': 'id'}
            network_two = {'name': 'network2', 'type': 'default', 'id': 'id'}
            self.valid_data['networks'].append(network)
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            gw.add_network(network_two)

    def test_add_network_before_start(self):
        """
        Test add_network action if gateway isn't started
        """
        with pytest.raises(StateCheckError,
                           message='action should raise an error if another network with the same type and id combination exists'):
            network = {'name': 'network', 'type': 'default', 'id': 'id'}
            gw = Gateway('gw', data=self.valid_data)
            gw.add_network(network)

    def test_remove_network(self):
        """
        Test remove_network action
        """
        network = {'name': 'network', 'type': 'default', 'id': 'id'}
        self.valid_data['networks'] = [network]
        gw = Gateway('gw', data=self.valid_data)
        gw.state.set('actions', 'start', 'ok')
        gw.remove_network('network')
        assert gw.data['networks'] == []
        gw._gateway_sal.deploy.assert_called_once_with()

    def test_remove_network_exception(self):
        """
        Test remove_network action raises exception
        """
        with pytest.raises(RuntimeError, message='actions should raise an error if deploy raises an exception'):
            network = {'name': 'network', 'type': 'default', 'id': 'id'}
            self.valid_data['networks'] = [network]
            gw = Gateway('gw', data=self.valid_data)
            gw.state.set('actions', 'start', 'ok')
            gw._gateway_sal.deploy.side_effect = RuntimeError
            gw.remove_network('network')
            assert gw.data['networks'] == [network]
            assert gw._gateway_sal.deploy.call_count == 2

    def test_remove_network_name_exist(self):
        """
        Test remove_network action if network with name doesnt exist
        """
        gw = Gateway('gw', data=self.valid_data)
        gw.state.set('actions', 'start', 'ok')
        gw.remove_network('network')

    def test_remove_network_before_start(self):
        """
        Test remove_network action if gateway isn't started
        """
        with pytest.raises(StateCheckError,
                           message='action should raise an error if another gateway isnt started'):
            gw = Gateway('gw', data=self.valid_data)
            gw.remove_network('network')

    def test_uninstall(self):
        """
        Test uninstall action
        """
        gw = Gateway('gw', data=self.valid_data)
        gw.state.set('actions', 'install', 'ok')
        gw.uninstall()
        gw._gateway_sal.stop.called_once_with()

    def test_stop(self):
        """
        Test uninstall action
        """
        gw = Gateway('gw', data=self.valid_data)
        gw.state.set('actions', 'start', 'ok')
        gw.stop()
        gw._gateway_sal.stop.called_once_with()

