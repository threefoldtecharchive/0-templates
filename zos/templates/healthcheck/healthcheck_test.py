from unittest.mock import MagicMock, patch, call
import os

from healthcheck import Healthcheck, _update_healthcheck_state, _update, NODE_CLIENT

from JumpScale9Zrobot.test.utils import ZrobotBaseTest


class TestHealthcheckTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), Healthcheck)
        cls.valid_data = {'node': 'node', 'alerta': ['alerta']}

    def setUp(self):
        patch('js9.j.clients', MagicMock()).start()

    def tearDown(self):
        patch.stopall()

    def test_create_with_valid_data(self):
        """
        Test create healthcheck service
        """
        healthcheck = Healthcheck(name='healthcheck', data=self.valid_data)
        assert healthcheck.data == self.valid_data

    def test_node_sal(self):
        """
        Test node_sal property
        """
        node_sal_return = 'node_sal'
        get_node = patch('js9.j.clients.zos.sal.get_node', MagicMock(return_value=node_sal_return)).start()
        healthcheck = Healthcheck(name='healthcheck', data=self.valid_data)
        node_sal = healthcheck.node_sal
        get_node.assert_called_with(NODE_CLIENT)
        assert node_sal == node_sal_return

    def test_healthcheck(self):
        """
        Test _healthcheck
        """
        update_healthcheck = patch('healthcheck._update_healthcheck_state', MagicMock()).start()
        healthcheck = Healthcheck(name='healthcheck', data=self.valid_data)

        # could be the recurring action already kicked in
        # so we count the difference in call count
        pre_exec = update_healthcheck.call_count
        healthcheck._healthcheck()
        assert update_healthcheck.call_count == pre_exec + 13

    def test_update_healthcheck_state_list(self):
        """
        Test called with list
        """
        update = patch('healthcheck._update', MagicMock()).start()
        healthcheck = MagicMock()
        _update_healthcheck_state(MagicMock(), [healthcheck, healthcheck])
        assert update.call_count == 2

    def test_update_healthcheck_state(self):
        """
        Test called with one healthcheck
        """
        update = patch('healthcheck._update', MagicMock()).start()
        healthcheck = MagicMock()
        _update_healthcheck_state(MagicMock(), healthcheck)
        assert update.call_count == 1

    def test_update_one_message(self):
        """
        Test called with one message
        """
        healthcheck = {'messages': [{'status': 'status'}], 'category': 'category', 'id': 'id'}
        service = MagicMock()
        _update(service, healthcheck)
        service.state.set.assert_called_once_with('category', 'id', 'status')

    def test_update_multiple_messages(self):
        """
        Test called with one message
        """
        healthcheck = {
            'messages': [{'status': 'status', 'id': 1},
                         {'status': 'status', 'id': 2}],
            'category': 'category',
            'id': 'id'
        }
        service = MagicMock()
        _update(service, healthcheck)
        service.state.set.assert_has_calls([call('category', 'id-1', 'status'), call('category', 'id-2', 'status')])

    def test_monitor_healthcheck(self):
        """
        Test _monitor action without reboot
        """
        healthcheck = Healthcheck(name='healthcheck', data=self.valid_data)
        healthcheck.api.services.get = MagicMock()
        healthcheck._healthcheck = MagicMock()
        healthcheck._monitor()

        healthcheck._healthcheck.assert_called_with()
