from tests.testcases.base_test import BaseTest
from nose_parameterized import parameterized
from Jumpscale import j
import unittest
import time, random, requests

@unittest.skip("https://github.com/threefoldtech/0-templates/issues/277")
class DmVm_Testcases(BaseTest):
    def tearDown(self):
        for vm in self.vms:
            vm.uninstall()
            vm.service.delete()
        self.vms.clear()
        super().tearDown()

    @parameterized.expand(['zero-os', 'ubuntu'])
    def test001_create_vm(self, os_type):
        """ ZRT-ZOS-032
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
        
    @parameterized.expand([('zero-os', 'ext4'), ('zero-os', 'ext3'), ('zero-os', 'ext2'), ('zero-os', 'btrfs'),
                           ('ubuntu', 'ext4'), ('ubuntu', 'ext3'), ('ubuntu', 'ext2'), ('ubuntu', 'btrfs')])
    def test002_attach_disk_to_vm(self, os_type, filesystem):
        """ ZRT-ZOS-033
        * Test case for adding vdisk to the vm.*

        **Test Scenario:**
        
        #. Create vm [VM] with disk [D], should succeed.
        #. Check that disk [D1] added successfully to vm.
        """
        if os_type == 'zero-os':
            # config is not working on current zos flist, and sal code is using config to make filesystem and mointpoint
            self.skipTest("https://github.com/threefoldtech/jumpscale_prefab/issues/32")

        self.log('Create vm [VM] with disk [D], should succeed.')
        vm = self.controller.dm_vm
        ssh_config = [{'path': '/root/.ssh/authorized_keys', 'content': self.ssh_key, 'name': 'sshkey'}]
        disk = [{'label': 'label',
                 'diskType': self.disk_type,
                 'size': random.randint(1, int(self.disk_size/10)),
                 'mountPoint':'/mnt/{}'.format(self.random_string()),
                 'filesystem': filesystem,
                 }]
        vm.install(wait=True, configs=ssh_config, ports=[], image=os_type, disks=disk)
        self.vms.append(vm)

        self.log('Get zerotier ip from vm info.')
        vm_zt_ip = self.get_dm_vm_zt_ip(vm)

        self.log('Check that disk [D1] added successfully to vm.')
        if os_type == 'zero-os':
            node = j.clients.zos.get(self.random_string(), data={'host': vm_zt_ip})
            disks = node.client.disks.list()
            self.assertEqual(len(disks), 1)
            disk_size = int(disks[0]['size']/(1024**3))
            self.assertEqual(disk_size, disk[0]['size'])
            self.assertEqual(disk[0]['fstype'], filesystem)
            self.assertEqual(disk[0]['mountpoint'], disk[0]['mountPoint'])            
        else:
            self.assertTrue(vm.info().result['disks']) 
            cmd = 'df -Th | grep {} '.format(disk[0]['mountPoint'])
            result = self.ssh_vm_execute_command(vm_ip=vm_zt_ip, cmd=cmd)
            disk_filesystem = result.split()[1]
            self.assertEqual(disk_filesystem, filesystem)
    
    @parameterized.expand(['zero-os', 'ubuntu'])
    def test003_add_remove_port_forward_to_vm(self, os_type):
        """ZRT-ZOS-034
        * Test case for adding/removing port forward to/from vm. *
        Test Scenario:

        #. Create vm[VM1], should succeed.
        #. Check vm info, ports should be empty.
        #. Add port forward [p1] to [VM1], should succeed.
        #. Check vm info again, ports should be found.
        #. Remove port forward [p1] from [VM1], should succeed.
        #. Check vm info again, ports should be empty.
        """
        self.log('Create vm[VM1], should succeed.')
        ssh_config = [{'path': '/root/.ssh/authorized_keys', 'content': self.ssh_key, 'name': 'sshkey'}]       
        vm = self.controller.dm_vm
        vm.install(wait=True, configs=ssh_config, ports=[], image=os_type)
        self.vms.append(vm)

        self.log("Check vm info, ports should be empty.")
        vms = self.controller.node.client.kvm.list()
        vm_info = [v for v in vms if vm.service.data['guid'] in v['name']]
        self.assertFalse(vm_info[0]['params']['port'])

        self.log('Add port forward [p1] to [VM1], should succeed.')
        port_name = self.random_string()   
        host_port = random.randint(3000, 4000)
        guest_port = random.randint(5000, 6000)
        vm.add_portforward(name=port_name, source=host_port, target=guest_port)

        self.log("Check vm info again, ports should be found.")
        vms = self.controller.node.client.kvm.list()
        vm_info = [v for v in vms if vm.service.data['guid'] in v['name']]
        port = {'{}'.format(host_port): guest_port}
        self.assertEqual(vm_info[0]['params']['port'], port)

        self.log('Remove port forward [p1] from [VM1], should succeed.')
        vm.remove_portforward(port_name)

        self.log("Check vm info again, ports should be empty.")
        vms = self.controller.node.client.kvm.list()
        vm_info = [v for v in vms if vm.service.data['guid'] in v['name']]
        self.assertFalse(vm_info[0]['params']['port'])

@unittest.skip("https://github.com/threefoldtech/0-templates/issues/277")
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
        """ ZRT-ZOS-035
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
        """ ZRT-ZOS-036
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
        """ ZRT-ZOS-037
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
        """ ZRT-ZOS-038
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