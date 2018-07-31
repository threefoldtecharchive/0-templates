from unittest import TestCase
from unittest.mock import MagicMock, patch, call
import tempfile
import shutil
import os

import pytest

from js9 import j
from vm import Vm, ZT_TEMPLATE_UID, VDISK_TEMPLATE_UID, VM_TEMPLATE_UID
from zerorobot.template.state import StateCheckError
from zerorobot import config
from zerorobot.template_uid import TemplateUID

from JumpScale9Zrobot.test.utils import ZrobotBaseTest


class TestVmTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), Vm)
        cls.valid_data = {
            'cpu': 1,
            'image': 'ubuntu',
            'memory': 128,
            'zerotier': {
                'id': 'id',
                'ztClient': 'main',
            },
            'disks': [{
                'diskType': 'hdd',
                'size': 10,
                'mountPoint': '/mnt',
                'filesystem': 'btrfs',
                'label': 'test',
            }],
            'configs': [],
            'ztIdentity': '',
            'nodeId': 'main',
        }
        cls.vnc_port = 5900

    def setUp(self):
        patch('js9.j.clients', MagicMock()).start()
        self.vm = Vm('vm', data=self.valid_data)
        self.vm._node_api = MagicMock()

    def tearDown(self):
        patch.stopall()

    def test_invalid_data(self):
        """
        Test creating a vm with invalid data
        """
        with pytest.raises(ValueError, message='template should fail to instantiate if data dict is missing the nodeId'):
            vm = Vm(name='vm', data={})
            vm.validate()

        with pytest.raises(ValueError, message='template should fail to instantiate if image is not valid'):
            vm = Vm(name='vm', data={'nodeId': 'main', 'image': 'test'})
            vm.validate()

        with pytest.raises(ValueError, message='template should fail to instantiate if zerotier dict is missing id'):
            vm = Vm(name='vm', data={'nodeId': 'main', 'image': 'ubuntu', 'zerotier': {'id': ''}})
            vm.validate()

        with pytest.raises(ValueError, message='template should fail to instantiate if zerotier dict is missing ztClient'):
            vm = Vm(name='vm', data={'nodeId': 'main', 'image': 'ubuntu', 'zerotier': {'id': 'id'}})
            vm.validate()

        with pytest.raises(ValueError, message='template should fail to instantiate if there are no nodes'):

            capacity = MagicMock()
            capacity.api.ListCapacity.return_value = ([],)
            patch('js9.j.clients.grid_capacity.get.return_value', capacity).start()
            self.vm.validate()

    def test_valid_data(self):
        """
        Test creating a vm service with valid data
        """
        capacity = MagicMock()
        capacity.api.GetCapacity.return_value = (MagicMock(robot_address='url'), None)
        patch('js9.j.clients.grid_capacity.get.return_value', capacity).start()
        vm = Vm('vm', data=self.valid_data)
        vm.validate()
        j.clients.zrobot.get.assert_called_with(self.valid_data['nodeId'], data={'url': 'url'})
        assert vm.data == self.valid_data

    def test_node_vm(self):
        """
        Test the _node_api property
        """
        self.vm._node_api.services.get = MagicMock(return_value='service')
        assert self.vm._node_vm == 'service'

    def test_install_vm(self):
        """
        Test successfully creating a vm
        """
        disk = self.valid_data['disks'][0]
        capacity = MagicMock()
        capacity.api.GetCapacity.return_value = (MagicMock(robot_address='url'), None)
        patch('js9.j.clients.grid_capacity.get.return_value', capacity).start()

        self.vm.validate()
        zt_client = MagicMock()
        zt_client.schedule_action.return_value.wait.return_value.result = 'token'
        self.vm.api.services.get = MagicMock(return_value=zt_client)
        vdisk_name = '_'.join([self.vm.guid, disk['label']])
        create = self.vm._node_api.services.find_or_create
        create.return_value.name = vdisk_name
        self.vm.install()
        zt_client.schedule_action.assert_called_once_with('add_to_robot', args={'serviceguid': self.vm.guid, 'url': 'url'})
        assert self.vm._node_api.services.find_or_create.call_count == 2

        disks = [{
            'name': vdisk_name,
            'mountPoint': disk['mountPoint'],
            'filesystem': disk['filesystem'],
            'label': disk['label'],
        }]

        vm_data = {
            'memory': self.valid_data['memory'],
            'cpu': self.valid_data['cpu'],
            'disks': disks,
            'configs': self.valid_data['configs'],
            'ztIdentity': self.valid_data['ztIdentity'],
            'nics': [{
                'id': self.valid_data['zerotier']['id'],
                'type': 'zerotier',
                'ztClient': self.vm.guid,
                'name': 'zerotier_nic',
            },
                {'name': 'test',
                 'type': 'default'
                 }],
            'flist': 'https://hub.gig.tech/gig-bootable/ubuntu:lts.flist'
        }
        vdisk_create = call(VDISK_TEMPLATE_UID, '_'.join([self.vm.guid, disk['label']]), data=disk)
        vm_create = call(VM_TEMPLATE_UID, self.vm.guid, data=vm_data)
        create.assert_has_calls([vdisk_create,  vm_create], any_order=True)
        self.vm.state.check('actions', 'install', 'ok')
        self.vm.state.check('status', 'running', 'ok')

    def test_uninstall_vm(self):
        """
        Test successfully destroying the vm
        """
        self.vm.state.set('actions', 'install', 'ok')
        self.vm.api = MagicMock()
        self.vm.uninstall()

        self.vm._node_vm.schedule_action.assert_called_with('uninstall')
        with pytest.raises(StateCheckError):
            self.vm.state.check('actions', 'install', 'ok')
        with pytest.raises(StateCheckError):
            self.vm.state.check('status', 'running', 'ok')

    def test_shutdown_vm_not_running(self):
        """
        Test shutting down the vm without creation
        """
        with pytest.raises(StateCheckError, message='Shuting down vm that is not running should raise an error'):
            self.vm.shutdown()

    def test_shutdown_vm(self):
        """
        Test successfully shutting down the vm
        """
        self.vm.state.set('status', 'running', 'ok')
        self.vm.state.delete = MagicMock()

        self.vm.shutdown()

        self.vm._node_vm.schedule_action.assert_called_with('shutdown')
        self.vm.state.check('status', 'shutdown', 'ok')
        self.vm.state.delete.assert_called_with('status', 'running')

    def test_pause_vm_not_running(self):
        """
        Test pausing the vm without creation
        """
        with pytest.raises(StateCheckError, message='Pausing vm that is not running'):
            self.vm.pause()

    def test_pause_vm(self):
        """
        Test successfully pausing the vm
        """
        self.vm.state.set('status', 'running', 'ok')
        self.vm.state.delete = MagicMock()
        self.vm.pause()

        self.vm._node_vm.schedule_action.assert_called_with('pause')
        self.vm.state.delete.assert_called_once_with('status', 'running')
        self.vm.state.check('actions', 'pause', 'ok')

    def test_resume_vm_not_pause(self):
        """
        Test resume the vm without creation
        """
        with pytest.raises(StateCheckError, message='Resuming vm before pause should raise an error'):
            self.vm.resume()

    def test_resume_vm(self):
        """
        Test successfully resume the vm
        """
        self.vm.state.set('actions', 'pause', 'ok')
        self.vm.state.delete = MagicMock()
        self.vm.resume()

        self.vm._node_vm.schedule_action.assert_called_with('resume')
        self.vm.state.check('status', 'running', 'ok')
        self.vm.state.delete.assert_called_once_with('actions', 'pause')

    def test_reboot_vm_not_installed(self):
        """
        Test reboot the vm without creation
        """
        with pytest.raises(StateCheckError, message='Rebooting vm before install should raise an error'):
            self.vm.reboot()

    def test_reboot_vm(self):
        """
        Test successfully reboot the vm
        """
        self.vm.state.set('actions', 'install', 'ok')
        self.vm.reboot()
        self.vm._node_vm.schedule_action.assert_called_with('reboot')
        self.vm.state.check('status', 'rebooting', 'ok')

    def test_reset_vm_not_installed(self):
        """
        Test reset the vm without creation
        """
        with pytest.raises(StateCheckError, message='Resetting vm before install should raise an error'):
            self.vm.reset()

    def test_reset_vm(self):
        """
        Test successfully reset the vm
        """
        self.vm.state.set('actions', 'install', 'ok')
        self.vm.reset()
        self.vm._node_vm.schedule_action.assert_called_with('reset')

    def test_enable_vnc_vm_not_installed(self):
        """
        Test enable_vnc vm not installed
        """
        with pytest.raises(StateCheckError, message='enable vnc before install should raise an error'):
            self.vm.enable_vnc()

    def test_enable_vnc(self):
        self.vm.state.set('actions', 'install', 'ok')
        self.vm.enable_vnc()
        self.vm._node_vm.schedule_action.assert_called_with('enable_vnc')

    def test_disable_vnc(self):
        """
        Test disable_vnc when there is a vnc port
        """
        self.vm.state.set('vnc', 90, 'ok')
        self.vm.state.set('actions', 'install', 'ok')
        self.vm.disable_vnc()
        self.vm._node_vm.schedule_action.assert_called_with('disable_vnc')

    def test_disable_vnc_before_enable(self):
        """
        Test disable vnc before enable
        :return:
        """
        with pytest.raises(StateCheckError, message='disable vnc before enable should raise an error'):
            self.vm.disable_vnc()

    def test_monitor_vm_not_running(self):
        """
        Test monitor vm not running
        """
        self.vm.state.set('actions', 'install', 'ok')
        self.vm._node_vm.state.check.side_effect = StateCheckError
        self.vm.state.delete = MagicMock()
        self.vm.state.set('actions', 'install', 'ok')

        self.vm._monitor()
        self.vm.state.delete.assert_called_once_with('status', 'running')

    def test_monitor_vm_running(self):
        """
        Test monitor vm running
        """
        self.vm.state.set('actions', 'install', 'ok')
        self.vm.state.delete = MagicMock()

        self.vm._monitor()
        assert self.vm.state.delete.call_count == 0

    def test_monitor_vm_not_installed(self):
        """
        Test monitor vm running
        """
        with pytest.raises(StateCheckError, message='disable vnc before enable should raise an error'):
            self.vm._monitor()
