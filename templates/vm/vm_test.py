from unittest.mock import MagicMock, patch
import os
import pytest

from jumpscale import j
from vm import Vm, NODE_CLIENT
from zerorobot.template.state import StateCheckError

from JumpScale9Zrobot.test.utils import ZrobotBaseTest


class TestVmTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), Vm)
        cls.valid_data = {
            'cpu': 1,
            'flist': 'flist',
            'memory': 128,
            'nics': [],
            'vnc': -1,
            'ports': [],
            'disks': [],
            'mounts': [],
            'tags': [],
            'uuid': '444d10d7-77f8-4b33-a6df-feb76e34dbc4',
            'configs': [],
            'ztIdentity': '',
            'ipxeUrl': '',

        }
        cls.vnc_port = 5900

    def setUp(self):
        patch('js9.j.clients.zos.sal.get_node', MagicMock()).start()

    def tearDown(self):
        patch.stopall()

    def test_invalid_data(self):
        """
        Test creating a vm with invalid data
        """
        with pytest.raises(ValueError, message='template should fail to instantiate if data dict is missing the node'):
            vm = Vm(name='vm', data={})
            vm.validate()

    def test_valid_data(self):
        """
        Test creating a vm service with valid data
        """
        vm = Vm('vm', data=self.valid_data)
        vm.validate()
        assert vm.data == self.valid_data

    def test_node_sal(self):
        """
        Test the _node_sal property
        """
        vm = Vm('vm', data=self.valid_data)
        node_sal_return = 'node_sal'
        patch('js9.j.clients.zos.sal.get_node',  MagicMock(return_value=node_sal_return)).start()

        assert vm._node_sal == node_sal_return
        j.clients.zos.sal.get_node.assert_called_with(NODE_CLIENT)

    def test_vm_sal(self):
        """
        Test the _vm_sal property
        """
        vm = Vm('vm', data=self.valid_data)
        vm_sal = 'vm_sal'
        vm._node_sal.primitives.from_dict.return_value = vm_sal
        assert vm._vm_sal == vm_sal

    def test_install_vm(self):
        """
        Test successfully creating a vm
        """
        vm = Vm('vm', data=self.valid_data)
        data = self.valid_data.copy()
        data['name'] = vm.name
        vm_sal = MagicMock(uuid='uuid')
        vm._node_sal.primitives.from_dict.return_value = vm_sal
        vm.install()
        assert 'uuid' == 'uuid'

        vm._node_sal.primitives.from_dict.called_once_with(data)
        vm.state.check('actions', 'install', 'ok')
        vm.state.check('status', 'running', 'ok')

    def test_uninstall_vm(self):
        """
        Test successfully destroying the vm
        """
        vm = Vm('vm', data=self.valid_data)
        vm.state.set('actions', 'install', 'ok')
        vm.uninstall()

        vm._vm_sal.destroy.assert_called_with()
        with pytest.raises(StateCheckError):
            vm.state.check('actions', 'install', 'ok')
        with pytest.raises(StateCheckError):
            vm.state.check('status', 'running', 'ok')

    def test_shutdown_vm_not_running(self):
        """
        Test shutting down the vm without creation
        """
        with pytest.raises(StateCheckError, message='Shuting down vm that is not running should raise an error'):
            vm = Vm('vm', data=self.valid_data)
            vm.shutdown()

    def test_shutdown_vm(self):
        """
        Test successfully shutting down the vm
        """
        vm = Vm('vm', data=self.valid_data)
        vm.state.set('status', 'running', 'ok')

        vm.shutdown()

        vm._vm_sal.shutdown.assert_called_with()

        with pytest.raises(StateCheckError):
            vm.state.check("status", 'running', 'ok')
        with pytest.raises(StateCheckError):
            vm.state.check("actions", 'start', 'ok')

    def test_pause_vm_not_running(self):
        """
        Test pausing the vm without creation
        """
        with pytest.raises(StateCheckError, message='Pausing vm that is not running'):
            vm = Vm('vm', data=self.valid_data)
            vm.pause()

    def test_pause_vm(self):
        """
        Test successfully pausing the vm
        """
        vm = Vm('vm', data=self.valid_data)
        vm.state.set('status', 'running', 'ok')
        vm.state.delete = MagicMock()

        vm.pause()

        vm._vm_sal.pause.assert_called_with()
        vm.state.delete.assert_called_once_with('status', 'running')
        vm.state.check('actions', 'pause', 'ok')

    def test_resume_vm_not_pause(self):
        """
        Test resume the vm without creation
        """
        with pytest.raises(StateCheckError, message='Resuming vm before pause should raise an error'):
            vm = Vm('vm', data=self.valid_data)
            vm.resume()

    def test_resume_vm(self):
        """
        Test successfully resume the vm
        """
        vm = Vm('vm', data=self.valid_data)
        vm.state.set('actions', 'pause', 'ok')
        vm.state.delete = MagicMock()
        vm.resume()

        vm._vm_sal.resume.assert_called_with()
        vm.state.check('status', 'running', 'ok')
        vm.state.delete.assert_called_once_with('actions', 'pause')

    def test_reboot_vm_not_installed(self):
        """
        Test reboot the vm without creation
        """
        with pytest.raises(StateCheckError, message='Rebooting vm before install should raise an error'):
            vm = Vm('vm', data=self.valid_data)
            vm.reboot()

    def test_reboot_vm(self):
        """
        Test successfully reboot the vm
        """
        vm = Vm('vm', data=self.valid_data)
        vm.state.set('actions', 'install', 'ok')
        vm.reboot()
        vm._vm_sal.reboot.assert_called_with()
        vm.state.check('status', 'rebooting', 'ok')

    def test_reset_vm_not_installed(self):
        """
        Test reset the vm without creation
        """
        with pytest.raises(StateCheckError, message='Resetting vm before install should raise an error'):
            vm = Vm('vm', data=self.valid_data)
            vm.reset()

    def test_reset_vm(self):
        """
        Test successfully reset the vm
        """
        vm = Vm('vm', data=self.valid_data)
        vm.state.set('actions', 'install', 'ok')
        vm.reset()
        vm._vm_sal.reset.assert_called_with()

    def test_enable_vnc_vm_not_installed(self):
        """
        Test enable_vnc vm not installed
        """
        with pytest.raises(StateCheckError, message='enable vnc before install should raise an error'):
            vm = Vm('vm', data=self.valid_data)
            vm.enable_vnc()

    def test_enable_vnc(self):
        vm = Vm('vm', data=self.valid_data)
        vm.state.set('actions', 'install', 'ok')
        vm_sal = MagicMock(info={'vnc': 90})
        vm._node_sal.primitives.from_dict.return_value = vm_sal
        vm.enable_vnc()
        vm._vm_sal.enable_vnc.assert_called_with()

    def test_disable_vnc(self):
        """
        Test disable_vnc when there is a vnc port
        """
        vm = Vm('vm', data=self.valid_data)
        vm.state.set('vnc', 90, 'ok')
        vm.state.set('actions', 'install', 'ok')
        vm.state.delete = MagicMock()
        vm_sal = MagicMock(info={'vnc': 90})
        vm._node_sal.primitives.from_dict.return_value = vm_sal
        vm.disable_vnc()
        vm._vm_sal.disable_vnc.assert_called_with()

    def test_disable_vnc_before_enable(self):
        """
        Test disable vnc before enable
        :return:
        """
        with pytest.raises(StateCheckError, message='disable vnc before enable should raise an error'):
            vm = Vm('vm', data=self.valid_data)
            vm.disable_vnc()

    def test_monitor_vm_not_running_deploy_fails(self):
        """
        Test monitor vm not running and deploy fails
        """
        vm = Vm('vm', data=self.valid_data)
        vm._vm_sal.is_running.return_value = False
        vm._vm_sal.deploy = MagicMock()
        vm.state.delete = MagicMock()
        vm.state.set('actions', 'install', 'ok')
        vm.state.set('actions', 'start', 'ok')

        vm._monitor()
        vm.state.delete.assert_called_once_with('status', 'running')
        vm._vm_sal.deploy.assert_called_once_with()

    def test_monitor_vm_not_running_deploy_success(self):
        """
        Test monitor vm not running and deploy fails
        """
        vm = Vm('vm', data=self.valid_data)
        vm._vm_sal.is_running.side_effect = [False, True]
        vm._vm_sal.deploy = MagicMock()
        vm.state.delete = MagicMock()
        vm.state.set('actions', 'install', 'ok')
        vm.state.set('actions', 'start', 'ok')

        vm._monitor()
        vm.state.check("status", "running", "ok")
        vm._vm_sal.deploy.assert_called_once_with()

    def test_monitor_vm_running(self):
        """
        Test monitor vm running
        """
        vm = Vm('vm', data=self.valid_data)
        vm.state.set('status', 'rebooting', 'ok')
        vm.state.set('actions', 'install', 'ok')
        vm.state.set('actions', 'start', 'ok')
        vm._vm_sal.is_running.return_value = True

        vm._monitor()

        vm.state.check('status', 'running', 'ok')
        with pytest.raises(StateCheckError):
            vm.state.check('status', 'rebooting', 'ok')

    def test_monitor_before_install(self):
        """
        Test monitor before install
        :return:
        """
        with pytest.raises(StateCheckError, message='monitor vm before install should raise an error'):
            vm = Vm('vm', data=self.valid_data)
            vm._monitor()
