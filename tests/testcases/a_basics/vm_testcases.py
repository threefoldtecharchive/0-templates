from tests.testcases.base_test import BaseTest
from nose_parameterized import parameterized
import unittest
import time, random
from jumpscale import j
import requests


class TESTVM(BaseTest):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        for vm in cls.vms:
            vm.uninstall()
        cls.vms.clear()

        for zdb in cls.zdbs:
            namespaces = zdb.namespace_list().result
            for namespace in namespaces:
                zdb.namespace_delete(namespace['name'])
            zdb.stop()
        cls.zdbs.clear()

        for vdisk in cls.vdisks:
            vdisk.uninstall()

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
        ssh_config = [{'path': '/root/.ssh/authorized_keys', 'content': self.ssh_key, 'name': 'sshkey'}]       
        vm1 = self.controller.vm_manager
        vm1.install(wait=True, configs=ssh_config)
        source_port = int(vm1.info().result['ports'].popitem()[0])

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
        vm = [vm for vm in vms if vm['name'] == vm1.vm_service_name]
        self.assertFalse(vm)

    def test002_create_vm_with_non_valid_params(self):
        """ ZRT-ZOS-004
        *Test case for creating vm with non-valid parameters*

        **Test Scenario:**
        #. Create a vm without providing flist parameter, should fail.

        """
        self.log('Create a vm without providing flist parameter, should fail.')
        vm_name = self.random_string()
        vm = self.controller.vm_manager

        with self.assertRaises(Exception) as e:
            vm.install(wait=True, name=vm_name, flist='')
        self.assertIn( "invalid input. Vm requires flist or ipxeUrl to be specifed.", e.exception.args[0])
    
    def test003_create_vm_with_zt_network(self):
        """ZRT-ZOS-013
        * Test case for creating a vm with zerotier netwotk.
        Test Scenario:

        #. Get zerotier client.
        #. Create vm[vm1] with zerotier network, should succeed.
        #. Get zerotier ip from vm info.
        #. Check that vm can be accessed by zertier network, should succeed.

        """
        self.log('Get zerotier client.')
        zt_id = self.config['zt']['zt_netwrok_id']
        zt_client = self.controller.zt_client
        zt_network = [{'name': self.random_string(), 'type': 'zerotier', 'id': zt_id, 'ztClient': zt_client.service_name}]

        self.log('Create vm[vm1] with zerotier network, should succeed.')
        ssh_config = [{'path': '/root/.ssh/authorized_keys', 'content': self.ssh_key, 'name': 'sshkey'}]
        vm = self.controller.vm_manager
        vm.install(wait=True, configs=ssh_config, nics=zt_network, ports=[])
        self.vms.append(vm)

        self.log('Get zerotier ip from vm info.')
        vm_zt_ip = self.get_zt_ip(vm)
        
        self.log('Check that vm can be accessed by zertier network, should succeed.')
        result = self.ssh_vm_execute_command(vm_ip=vm_zt_ip, cmd='pwd')
        self.assertEqual(result, '/root')
        self.log('Remove zerotier service')
        zt_client.delete()
        
    def test004_add_remove_port_forward_to_vm(self):
        """ZRT-ZOS-014
        * Test case for adding and removing port forward to vm.
        Test Scenario:

        #. Create vm [VM1], should succeed.
        #. Add port forward [p1] to [VM1], should succeed.
        #. Start server on [P1], should succeed.
        #. Check that you can access that server through [P1] and get a file.
        #. remove port forward [p1].
        #. Check that you can't access the server anymore.

        """
        self.log('Create vm[vm1], should succeed.')
        ssh_config = [{'path': '/root/.ssh/authorized_keys', 'content': self.ssh_key, 'name': 'sshkey'}]       
        vm = self.controller.vm_manager
        vm.install(wait=True, configs=ssh_config)
        self.vms.append(vm)
        ssh_port = int(vm.info().result['ports'].popitem()[0])

        self.log('Add port forward [p1] to [VM1], should succeed.')
        port_name = self.random_string()   
        host_port = random.randint(3000, 4000)
        guest_port = random.randint(5000, 6000)
        vm.add_portforward(name=port_name, source=host_port, target=guest_port)

        self.log('Start server on [P1], should succeed.')
        cmd = 'python3 -m http.server {} &> /tmp/server.log &'.format(guest_port)
        self.ssh_vm_execute_command(vm_ip=self.node_ip, port=ssh_port, cmd=cmd)
        time.sleep(10)

        self.log("Get the content of authorized_key file from the vm using the server created ")
        response = requests.get('http://{}:{}/.ssh/authorized_keys'.format(self.node_ip, host_port))
        content = response.content.decode('utf-8')

        self.log("Make sure that ssh key is in the authorized_key")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(content, self.ssh_key)

        self.log('remove port forward [p1]')
        vm.remove_portforward(port_name)

        self.log("Check that you can't access the server anymore")
        with self.assertRaises(Exception):
            requests.get('http://{}:{}/.ssh/authorized_keys'.format(self.node_ip, host_port))

    @parameterized.expand([('ext4', 'hdd'), ('ext4', 'ssd'), ('ext3', 'hdd'), ('ext3', 'ssd'),
                            ('ext2', 'hdd'), ('ext2', 'ssd'), ('btrfs', 'hdd'), ('btrfs', 'ssd')])
    def test005_add_vdisk_from_vm(self, filesystem, disk_type):
        """ ZRT-ZOS-015
        * Test case for adding vdisk to the vm.
        **Test Scenario:**
        
        #. Create zerodb [zdb], should succeed.
        #. Create vdisk [D] using namespace on [zdb], should succeed.
        #. Create vm [VM] with disk [D], should succeed.
        #. Check that disk [D1] added successfully to vm.

        """
        self.log('Create zerodb [zdb], should succeed.')
        zdb_name = self.random_string()
        zdb = self.controller.zdb_manager
        zdb.install(wait=True, path=self.mount_paths[0], name=zdb_name)
        self.zdbs.append(zdb)

        self.log('Create vdisk [D] using namespace on [zdb], should succeed.')
        disk_name = self.random_string()
        vdisk = self.controller.vdisk
        vdisk.install(zerodb=zdb_name, nsName=disk_name, filesystem=filesystem, diskType=disk_type)
        self.vdisks.append(vdisk)

        self.log('Create vm [VM] with disk [D], should succeed.')
        vm = self.controller.vm_manager
        ssh_config = [{'path': '/root/.ssh/authorized_keys', 'content': self.ssh_key, 'name': 'sshkey'}]
        disk = [{'name': disk_name,
                 'url': vdisk.url().result,
                 'mountPoint':'/mnt/{}'.format(disk_name),
                 'filesystem': filesystem,
                 'label': 'label'}]
        vm.install(wait=True, configs=ssh_config, disks=disk)
        self.vms.append(vm)

        self.log('Check that disk [D1] added successfully to vm.')
        self.assertTrue(vm.info().result['disks']) 
        ssh_port = int(vm.info().result['ports'].popitem()[0])
        result = self.ssh_vm_execute_command(vm_ip=self.node_ip, port=ssh_port, cmd='ls /mnt')
        self.assertEqual(result, disk_name)

class VM_actions(BaseTest):

    @classmethod
    def setUpClass(cls):
        self = cls()
        ssh_config = [{'path': '/root/.ssh/authorized_keys', 'content': self.ssh_key, 'name': 'sshkey'}]       
        cls.vm = self.controller.vm_manager
        cls.vm.install(wait=True, configs=ssh_config)
        cls.source_port = int(cls.vm.info().result['ports'].popitem()[0])
        result = self.ssh_vm_execute_command(vm_ip=self.node_ip, port=self.source_port, cmd='pwd')
        self.assertEqual(result, '/root')

    @classmethod
    def tearDownClass(cls):
        cls.vm.uninstall()

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