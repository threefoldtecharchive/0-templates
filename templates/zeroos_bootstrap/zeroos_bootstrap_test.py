from unittest.mock import MagicMock, patch
import os
import pytest

from zeroos_bootstrap import ZeroosBootstrap
from zerorobot.template.state import StateCheckError
from zerorobot.service_collection import ServiceNotFoundError

from JumpScale9Zrobot.test.utils import ZrobotBaseTest, mock_decorator


patch('zerorobot.template.decorator.timeout', MagicMock(return_value=mock_decorator)).start()
patch("gevent.sleep", MagicMock()).start()


class TestBootstrapTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), ZeroosBootstrap)
        cls.valid_data = {
            'zerotierClient': 'zt', 'wipeDisks': False,
            'zerotierNetID': '', 'redisPassword': '', 'networks': ['storage']
        }
        cls.member = {
            'nodeId': 'id', 'config': {'authorized': False, 'ipAssignments': []},
            'online': False, 'name': 'name'
        }
        cls.member2 = {
            'nodeId': 'id', 'config': {'authorized': False, 'ipAssignments': ['127.0.0.1']}
        }

    def setUp(self):
        patch('js9.j.clients.zerotier.get', MagicMock()).start()

    def tearDown(self):
        patch.stopall()

    def test_invalid_data(self):
        """
        Test creating service with invalid data
        """
        with pytest.raises(RuntimeError, message='Template should raise error if data is invalid'):
            bootstrap = ZeroosBootstrap('bootstrap', data={})
            bootstrap.validate()

        # test that the network service doesn't exist
        with pytest.raises(
                ServiceNotFoundError, message='Template should raise error if network service doesn\'t exist'):
            bootstrap = ZeroosBootstrap('bootstrap', data=self.valid_data)
            bootstrap.validate()

    def test_valid_data(self):
        """
        Test creating service with valid data
        """
        bootstrap = ZeroosBootstrap('bootstrap', data=self.valid_data)
        bootstrap.api.services = MagicMock()
        bootstrap.validate()
        assert bootstrap.data == self.valid_data

    def test_bootstrap(self):
        """
        Test creating service with valid data
        """
        bootstrap = ZeroosBootstrap('bootstrap', data=self.valid_data)
        bootstrap.api.get_robot = MagicMock()
        bootstrap._add_node = MagicMock(side_effect=[Exception, None])
        bootstrap._unauthorize_member = MagicMock()
        resp = MagicMock()
        resp.json = MagicMock(return_value=['member1', 'member2'])
        bootstrap._zt.client.network.listMembers = MagicMock(return_value=resp)
        bootstrap.bootstrap()

        bootstrap._unauthorize_member.assert_called_once_with('member1')

    def test_authorize_member(self):
        """
        Test authorize member
        """
        bootstrap = ZeroosBootstrap('bootstrap', data=self.valid_data)
        bootstrap._authorize_member(self.member)

        bootstrap._zt.client.network.updateMember.called_once_with(
            self.member, self.member['nodeId'], bootstrap.data['zerotierNetID'])

    def test_unauthorize_member(self):
        """
        Test unauthorize member
        """
        bootstrap = ZeroosBootstrap('bootstrap', data=self.valid_data)
        bootstrap._unauthorize_member(self.member)

        bootstrap._zt.client.network.updateMember.called_once_with(
            self.member, self.member['nodeId'], bootstrap.data['zerotierNetID'])

    def test_wait_member_ip(self):
        """
        Test _wait_member_ip
        """
        patch("zerorobot.template.decorator.timeout").start()
        bootstrap = ZeroosBootstrap('bootstrap', data=self.valid_data)

        resp = MagicMock()
        resp.json = MagicMock(return_value=self.member)
        resp2 = MagicMock()
        resp2.json = MagicMock(return_value=self.member2)
        bootstrap._zt.client.network.getMember = MagicMock(side_effect=[resp, resp2])
        zerotier_ip = bootstrap._wait_member_ip(self.member)

        assert zerotier_ip == '127.0.0.1'
        assert bootstrap._zt.client.network.getMember.call_count == 2

    def test_get_node_sal(self):
        """
        Test _get_node_sal
        """
        zero_os = patch('js9.j.clients.zos.get', MagicMock()).start()
        bootstrap = ZeroosBootstrap('bootstrap', data=self.valid_data)
        ip = '127.0.0.1'
        data = {
            'host': ip,
            'port': 6379,
            'password_': "",
            'db': 0,
            'ssl': True,
            'timeout': 120,
        }
        patch('js9.j.clients.zos.sal.get_node', MagicMock(return_value='node')).start()
        node = bootstrap._get_node_sal(ip)

        zero_os.called_once_with(instance='bootstrap', data=data, create=True, die=True)
        assert node == 'node'

    def test_ping_node(self):
        """
        Test ping node
        """
        patch("zerorobot.template.decorator.timeout").start()
        bootstrap = ZeroosBootstrap('bootstrap', data=self.valid_data)
        bootstrap.logger = MagicMock()
        node_sal = MagicMock()
        node_sal.client.ping = MagicMock(side_effect=[Exception, True])
        bootstrap._ping_node(node_sal, MagicMock())

        # ensure the loop is working when ping raises an exception
        assert node_sal.client.ping.call_count == 2

    def test_delete_node(self):
        """
        Test delete node deletes only the node with the right ip
        """
        bootstrap = ZeroosBootstrap('bootstrap', data=self.valid_data)
        bootstrap._unauthorize_member = MagicMock()
        resp = MagicMock()
        resp.json = MagicMock(return_value=[self.member, self.member2])
        bootstrap._zt.client.network.listMembers = MagicMock(return_value=resp)
        bootstrap.delete_node('127.0.0.1')

        bootstrap._unauthorize_member.assert_called_with(self.member2)

    def test_add_node_not_online(self):
        """
        Test add a node that is not online
        """
        self.member['online'] = False
        bootstrap = ZeroosBootstrap('bootstrap', data=self.valid_data)
        bootstrap._authorize_member = MagicMock()
        bootstrap._add_node(self.member)

        bootstrap._authorize_member.assert_not_called()

    def test_add_node_not_authorized(self):
        """
        Test add_node with node not authorized
        """
        self.member['online'] = True
        self.member['config']['authorized'] = True
        bootstrap = ZeroosBootstrap('bootstrap', data=self.valid_data)
        bootstrap._authorize_member = MagicMock()
        bootstrap._add_node(self.member)

        bootstrap._authorize_member.assert_not_called()

    def test_add_node_already_exists(self):
        """
        Test adding a node that already exists in the services
        """
        self.member['online'] = True
        self.member['config']['authorized'] = False
        bootstrap = ZeroosBootstrap('bootstrap', data=self.valid_data)
        bootstrap._authorize_member = MagicMock()
        bootstrap._wait_member_ip = MagicMock()
        bootstrap._get_node_sal = MagicMock()
        bootstrap._ping_node = MagicMock()
        hw = MagicMock()
        node = MagicMock()

        bootstrap.api.services.find = MagicMock(side_effect=[[hw], [node]])
        bootstrap._add_node(self.member)

        bootstrap._authorize_member.assert_called_once_with(self.member)
        assert hw.schedule_action.call_count == 1
        assert node.schedule_action.call_count == 1

    def test_add_node_already_exists_install_not_ok(self):
        """
        Test adding a node that already exists in the services but install state is not ok
        """
        self.member['online'] = True
        self.member['config']['authorized'] = False
        bootstrap = ZeroosBootstrap('bootstrap', data=self.valid_data)
        bootstrap._authorize_member = MagicMock()
        bootstrap._wait_member_ip = MagicMock()
        bootstrap._get_node_sal = MagicMock()
        bootstrap._ping_node = MagicMock()
        hw = MagicMock()
        node = MagicMock()
        node.state.check.side_effect = StateCheckError

        bootstrap.api.services.find = MagicMock(side_effect=[[hw], [node], []])
        bootstrap.api.services.create = MagicMock()
        bootstrap._add_node(self.member)
        assert node.delete.call_count == 1

    def test_add_node(self):
        """
        Test adding a node that doesn't exist in the services
        """
        self.member['online'] = True
        self.member['config']['authorized'] = False
        self.valid_data['wipeDisks'] = True
        bootstrap = ZeroosBootstrap('bootstrap', data=self.valid_data)
        bootstrap._authorize_member = MagicMock()
        bootstrap._wait_member_ip = MagicMock()
        node_sal = MagicMock(name='name')
        node_sal.client_info.os = MagicMock(return_value={'hostname': 'zero-os'})
        bootstrap._get_node_sal = MagicMock(return_value=node_sal)
        bootstrap._ping_node = MagicMock()

        erp = MagicMock()
        bootstrap.api.services.find = MagicMock(side_effect=[[], [], [erp]])
        bootstrap.api.services.create = MagicMock()
        bootstrap._add_node(self.member)

        bootstrap._authorize_member.assert_called_once_with(self.member)
        bootstrap._zt.client.network.updateMember(self.member, self.member['nodeId'], bootstrap.data['zerotierNetID'])
        node_sal.wipedisks.assert_called_once_with()
        erp.schedule_action.assert_called_once_with('register', args={'node_name': node_sal.name})

    def test_add_node_install_timeout(self):
        """
        Test adding a node that times out during creation
        """
        with pytest.raises(TimeoutError, message='template should raise timeout error if task install took too long'):
            self.member['online'] = True
            self.member['config']['authorized'] = False
            self.valid_data['wipeDisks'] = True
            bootstrap = ZeroosBootstrap('bootstrap', data=self.valid_data)
            bootstrap._authorize_member = MagicMock()
            bootstrap._wait_member_ip = MagicMock()
            node_sal = MagicMock(name='name')
            node_sal.client_info.os = MagicMock(return_value={'hostname': 'zero-os'})
            bootstrap._get_node_sal = MagicMock(return_value=node_sal)
            bootstrap._ping_node = MagicMock()

            bootstrap.api.services.find = MagicMock(side_effect=[[], []])
            node = MagicMock()
            task_install = MagicMock()
            task_install.wait = MagicMock(side_effect=TimeoutError)
            node.schedule_action = MagicMock(return_value=task_install)
            bootstrap.api.services.create = MagicMock(return_value=node)
            bootstrap._add_node(self.member)

            node.delete.called_once_with()

    def test_add_node_install_error(self):
        """
        Test adding a node that has state error during install
        """
        with pytest.raises(RuntimeError, message='template should raise RuntimeError if task install has state error'):
            self.member['online'] = True
            self.member['config']['authorized'] = False
            self.valid_data['wipeDisks'] = True
            bootstrap = ZeroosBootstrap('bootstrap', data=self.valid_data)
            bootstrap._authorize_member = MagicMock()
            bootstrap._wait_member_ip = MagicMock()
            node_sal = MagicMock(name='name')
            node_sal.client_info.os = MagicMock(return_value={'hostname': 'zero-os'})
            bootstrap._get_node_sal = MagicMock(return_value=node_sal)
            bootstrap._ping_node = MagicMock()

            bootstrap.api.services.find = MagicMock(side_effect=[[], []])
            node = MagicMock()
            task_install = MagicMock(state='error')
            node.schedule_action = MagicMock(return_value=task_install)
            bootstrap.api.services.create = MagicMock(return_value=node)
            bootstrap._add_node(self.member)

            node.delete.called_once_with()
