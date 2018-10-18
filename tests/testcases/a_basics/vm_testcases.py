from tests.testcases.base_test import BaseTest
from nose_parameterized import parameterized
import unittest
import time, random


class TESTVM(BaseTest):
    def setUp(self):
        super().setUp()

    def test001_create_vm(self):
        """ ZRT-ZOS-003
        *Test case for creating a vm.*

        **Test Scenario:**

        #. Create vm[vm1], should succeed.
        #. Check that the vm have been created.
        #. Destroy [vm1], should succeed.
        #. Check that [vm1] has been destroyed successfully.
        """
        self.log('Create vm[vm1], should succeed.')
        vm_name = self.random_string()
        source_port = random.randint(1000, 2000)
        port_name = self.random_string()
        port = [{'name': port_name, 'source': source_port, 'target': 22}]
        data = self.get_vm_default_data(name=vm_name, ports=port)        
        vm1 = self.controller.vm_manager
        vm1.install(data, wait=True)

        self.log('Check that the vm have been created.')
        self.assertTrue(vm1.install_state, " Installtion state is False")

        state = vm1.info().result['status']
        self.assertEqual(state, "running")

        result = self.ssh_vm_execute_command(vm_ip=self.node_ip, port=source_port, cmd='pwd')
        self.assertEqual(result, '/root')

        self.log('Destroy [vm1], should succeed.')
        vm1.uninstall(wait=True)

        self.log("Check that [vm1] has been destroyed successfully.")
        vms = self.controller.node.client.kvm.list()
        vm = [vm for vm in vms if vm['name'] == vm_name]
        self.assertFalse(vm)


    def test002_create_vm_with_non_valid_params(self):
        """ ZRT-ZOS-004
        *Test case for creating vm with non-valid parameters*

        **Test Scenario:**
        #. Create a vm without providing flist parameter, should fail.

        """
        self.log('Create a vm without providing flist parameter, should fail.')
        vm_name = self.random_string()
        data = self.get_vm_default_data(name=vm_name, flist='')
        vm = self.controller.vm_manager

        with self.assertRaises(Exception) as e:
            vm.install(data, wait=True)
        self.assertIn( "invalid input. Vm requires flist or ipxeUrl to be specifed.", e.exception.args[0])

    
class VM_actions(BaseTest):

    def setUp(self):
        super().setUp()
        self.vm_name = self.random_string()
        self.port_name = self.random_string()
        self.source_port = random.randint(1000, 2000)
        port = [{'name': self.port_name, 'source': self.source_port, 'target': 22}]
        self.data = self.get_vm_default_data(name=self.vm_name, ports=port)
        self.vm = self.controller.vm_manager
        self.vm.install(self.data, wait=True)
        result = self.ssh_vm_execute_command(vm_ip=self.node_ip, port=self.source_port, cmd='pwd')
        self.assertEqual(result, '/root')

    def teardown(self):
        self.vm.uninstall()

    def test001_pause_and_resume_vm(self):
        """ ZRT-ZOS-005
        *Test case for testing pause and resume vm*

        **Test Scenario:**

        #. Create a vm[vm1]  on node, should succeed.
        #. Pause [vm1], should succeed.
        #. Check that [vm1] has been paused successfully.
        #. Resume [vm1], should succeed.
        #. Check that [vm1] is runninng .
        """
        self.log('Pause [vm1], should succeed.')
        self.vm.pause()

        self.log("Check that [vm1] has been paused successfully.")
        state = self.vm.info().result['status']
        self.assertEqual(state, 'paused')
        result = self.execute_command(ip=self.node_ip, port=self.source_port, cmd='pwd')
        self.assertTrue(result.returncode)

        self.log("Resume [vm1], should succeed.")
        self.vm.resume()

        self.log('Check that [vm1] is runninng ')
        state = self.vm.info().result['status']
        self.assertEqual(state, "running")
        result = self.ssh_vm_execute_command(vm_ip=self.node_ip, port=self.source_port, cmd='pwd')
        self.assertEqual(result, '/root')

    def test002_shutdown_and_start_vm(self):
        """ ZRT-ZOS-006
        *Test case for testing shutdown and reset vm*

        **Test Scenario:**

        #. Create a vm[vm1]  on node, should succeed.
        #. Shutdown [vm1], should succeed.
        #. Check that [vm1] has been forced shutdown successfully.
        #. Start [vm1], should succeed.
        #. Check that [vm1] is running again.
        """
        self.log('Shutdown [vm1], should succeed.')
        self.vm.shutdown()

        self.log("Check that [vm1] has been forced shutdown successfully.")       
        for _ in range(40):
            state = self.vm.info().result['status']
            if state == 'halted':
                break
            else:
                time.sleep(5)
        else:
            self.assertEqual(state, 'halted', 'Take long time to shutdown')
        
        self.log("Start [vm1], should succeed.")
        self.vm.start()

        self.log("Check that [vm1] is running again.")
        result = self.ssh_vm_execute_command(vm_ip=self.node_ip, port=self.source_port, cmd='pwd')
        self.assertEqual(result, '/root')

    def test003_enable_and_disable_vm_vnc(self):
        """ ZRT-ZOS-007
        *Test case for testing reset vm*

        **Test Scenario:**

        #. Create a vm[vm1]  on node, should succeed.
        #. Enable vnc_port for [vm1], should succeed.
        #. Check that vnc_port has been enabled successfully.
        #. Disable vnc_port for [vm1], should succeed.
        #. Check that vnc_port has been disabled successfully.
        """
        self.log('Enable vnc_port for [vm1], should succeed.')
        self.vm.enable_vnc()

        self.log("Check that vnc_port has been enabled successfully.")
        info = self.controller.vm_manager.info()
        vnc_port = info.result['vnc'] - 5900
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
        """ ZRT-ZOS-008
        *Test case for testing reset vm*

        **Test Scenario:**

        #. Create a vm[vm1]  on node, should succeed.
        #. Reset or reboot the vm, should suceeed.
        #. Check that [vm] has been rebooted/reset successfully.
        """
        self.log('Reset or reboot the vm, should suceeed.')
        if action_type == "reset":
            self.vm.reset()
        else:
            self.vm.reboot()
        
        self.log('Check that [vm] has been rebooted/reset successfully.')
        reboot_response = self.ssh_vm_execute_command(vm_ip=self.node_ip, port=self.source_port, cmd='uptime')
        x = reboot_response.stdout.strip()
        uptime = int(x[x.find('up') + 2 : x.find('min')])
        self.assertAlmostEqual(uptime, 1 , delta=3)