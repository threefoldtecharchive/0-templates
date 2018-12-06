from tests.testcases.base_test import BaseTest
from nose_parameterized import parameterized
from Jumpscale import j
import unittest
import time, random, requests


class DmVm_Testcaes(BaseTest):
    def tearDown(self):
        for vm in self.vms:
            vm.uninstall()
            vm.service.delete()
        self.vms.clear()
        super().tearDown()

    @parameterized.expand(['zero-os', 'ubuntu'])
    def test001_create_vm(self, os_type):
        """ ZRT-ZOS-036
        *Test case for creating a vm.*

        **Test Scenario:**

        #. Create vm[vm1], should succeed.
        #. Get zerotier ip from vm info.
        #. Check that vm can be accessed by zertier network, should succeed.
        """
        self.log('Create vm[vm1], should succeed.')
        ssh_config = [{'path': '/root/.ssh/authorized_keys', 'content': self.ssh_key, 'name': 'sshkey'}]       
        vm = self.controller.dm_vm
        vm.install(wait=True, configs=ssh_config, ports=[], image=os_type)
        self.vms.append(vm)

        self.log('Get zerotier ip from vm info.')
        vm_zt_ip = self.get_dm_vm_zt_ip(vm)

        self.log('Check that vm can be accessed by zertier network, should succeed.')
        if os_type == 'zero-os':
            node = j.clients.zos.get(self.random_string(), data={'host': vm_zt_ip})
            pong = node.ping().split()[0]
            self.assertEqual(pong, 'PONG')
        else:
            result = self.ssh_vm_execute_command(vm_ip=vm_zt_ip, cmd='pwd')
            self.assertEqual(result, '/root')

class DMVM_actions(BaseTest):
    
    def setUp(self):
        ssh_config = [{'path': '/root/.ssh/authorized_keys', 'content': self.ssh_key, 'name': 'sshkey'}]       
        self.vm = self.controller.dm_vm
        self.vm.install(wait=True, configs=ssh_config)

        self.log('Get zerotier ip from vm info.')
        self.vm_zt_ip = self.get_dm_vm_zt_ip(self.vm)

        result = self.ssh_vm_execute_command(vm_ip=self.vm_zt_ip, cmd='pwd')
        self.assertEqual(result, '/root')

    def tearDown(self):
        for vm in self.vms:
            vm.uninstall()
            vm.service.delete()
        self.vms.clear()
        super().tearDown()

    def test001_pause_and_resume_vm(self):
        """ ZRT-ZOS-037
        *Test case for testing pause and resume vm*

        **Test Scenario:**

        #. Create a vm[vm1]  on node, should succeed.
        #. Pause [vm1], should succeed.
        #. Check that [vm1] has been paused successfully.
        #. Resume [vm1], should succeed.
        #. Check that [vm1] is runninng .
        """
        self.vms.append(self.vm)
        self.log('Pause [vm1], should succeed.')
        self.vm.pause()

        self.log("Check that [vm1] has been paused successfully.")
        state = self.vm.info().result['status']
        self.assertEqual(state, 'paused')
        result = self.execute_command(ip=self.vm_zt_ip, cmd='pwd')
        self.assertTrue(result.returncode)

        self.log("Resume [vm1], should succeed.")
        self.vm.resume()

        self.log('Check that [vm1] is runninng ')
        state = self.vm.info().result['status']
        self.assertEqual(state, "running")
        result = self.ssh_vm_execute_command(vm_ip=self.vm_zt_ip, cmd='pwd')
        self.assertEqual(result, '/root')

    @parameterized.expand(['shutdown', 'uninstall'])
    def test002_shutdown_vm(self, action):
        """ ZRT-ZOS-038
        *Test case for testing shutdown and uninstall vm*

        **Test Scenario:**

        #. Create a vm[vm1]  on node, should succeed.
        #. Shutdown/uninstall [vm1], should succeed.
        #. Wait untill [vm1] shutdown.
        #. Check that [vm1] has been shutdown/uninstalled successfully.
        """
        self.log('Shutdown/uninstall [vm1], should succeed.')
        if action == 'shutdown':
            self.vm.shutdown()

            self.log("Wait untill [vm1] shutdown..")       
            for _ in range(40):
                state = self.vm.info().result['status']
                if state == 'halted':
                    break
                else:
                    time.sleep(5)
            else:
                self.assertEqual(state, 'halted', 'Take long time to shutdown')
        else:
            self.vm.uninstall()
        self.vm.service.delete()

        self.log("Check that [vm1] has been shutdown/uninstalled successfully.")
        vms = self.controller.node.client.kvm.list()
        vm = [vm for vm in vms if self.vm.service.data['guid'] in vm['name']]
        self.assertFalse(vm)

    def test003_enable_and_disable_vm_vnc(self):
        """ ZRT-ZOS-039
        *Test case for testing enable and disable vnc port*

        **Test Scenario:**

        #. Create a vm[vm1]  on node, should succeed.
        #. Enable vnc_port for [vm1], should succeed.
        #. Check that vnc_port has been enabled successfully.
        #. Disable vnc_port for [vm1], should succeed.
        #. Check that vnc_port has been disabled successfully.
        """
        self.vms.append(self.vm)
        self.log('Enable vnc_port for [vm1], should succeed.')
        self.vm.enable_vnc()

        self.log("Check that vnc_port has been enabled successfully.")
        info = self.vm.info().result
        vnc_port = info['vnc'] - 5900
        response = self.check_vnc_connection('{}:{}'.format(self.node_ip, vnc_port))
        self.assertFalse(response.returncode)

        self.log("Disable vnc_port for [vm1], should succeed.")
        self.vm.disable_vnc()
        
        response = self.check_vnc_connection('{}:{}'.format(self.node_ip, vnc_port))
        self.assertTrue(response.returncode)
        self.assertIn('timeout caused connection failure', response.stderr.strip())

    @parameterized.expand(["reset", "reboot"])    
    @unittest.skip("https://github.com/threefoldtech/0-core/issues/35")
    def test004_reset_and_reboot_vm(self, action_type):
        """ ZRT-ZOS-040
        *Test case for testing reset and reboot vm*

        **Test Scenario:**

        #. Create a vm[vm1]  on node, should succeed.
        #. Reset or reboot the vm, should suceeed.
        #. Check that [vm] has been rebooted/reset successfully.
        """
        self.vms.append(self.vm)
        self.log('Reset or reboot the vm, should suceeed.')
        if action_type == "reset":
            self.vm.reset()
        else:
            self.vm.reboot()
        
        self.log('Check that [vm] has been rebooted/reset successfully.')
        reboot_response = self.ssh_vm_execute_command(vm_ip=self.vm_zt_ip, cmd='uptime')
        x = reboot_response.stdout.strip()
        uptime = int(x[x.find('up') + 2 : x.find('min')])
        self.assertAlmostEqual(uptime, 1 , delta=3)