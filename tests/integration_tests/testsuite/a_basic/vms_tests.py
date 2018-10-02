import unittest
from framework.zos_utils.utils import ZOS_BaseTest
from random import randint
import time
from nose_parameterized import parameterized
from random import randint

class BasicTests(ZOS_BaseTest):
    def __init__(self, *args, **kwargs):
        super(BasicTests, self).__init__(*args, **kwargs)

    @classmethod
    def setUpClass(cls):
        super(BasicTests, cls).setUpClass()

    def setUp(self):
        super(BasicTests, self).setUp()
        self.temp_actions = {
                             'vm': {'actions': ['install'],'service':''}
                            }

    def test001_create_vm(self):
        """ ZRT-ZOS-003
        *Test case for creating a vm.*

        **Test Scenario:**

        #. Create vm[vm1], should succeed.
        #. Check that the vm have been created.
        #. Destroy [vm1], should succeed.
        #. Check that [vm1] has been destroyed successfully.
        """
        self.log('%s STARTED' % self._testID)

        self.log('Create vm[vm1], should succeed.')
        vm1_name = self.random_string()
        self.vms = {vm1_name: {'flist': self.vm_flist, 'memory': 2048}}
        self.temp_actions['vm']['service']=vm1_name
        res = self.create_vm(vms=self.vms, temp_actions=self.temp_actions)
        self.assertEqual(type(res), type(dict()))
        self.wait_for_service_action_status(vm1_name, res[vm1_name]['install'])
        self.log('Check that the vm have been created.')
        time.sleep(3)
        vms = self.zos_client.kvm.list()
        vm = [vm for vm in vms if vm['name'] == vm1_name]
        self.assertTrue(vm)
        self.assertEqual(vm[0]['state'], "running")

        self.log('Destroy [vm1], should succeed.')
        temp_actions = {'vm': {'actions': ['uninstall'], 'service': vm1_name}}
        res = self.create_vm(vms=self.vms, temp_actions=temp_actions)
        self.assertEqual(type(res), type(dict()))
        self.wait_for_service_action_status(vm1_name, res[vm1_name]['uninstall'])        
        
        self.log("Check that [vm1] has been destroyed successfully.")
        vms = self.zos_client.kvm.list()
        vm = [vm for vm in vms if vm['name'] == vm1_name]
        self.assertFalse(vm)        
        self.log('%s ENDED' % self._testID)

    def test002_create_vm_with_non_valid_params(self):
        """ ZRT-ZOS-004
        *Test case for creating vm with non-valid parameters*

        **Test Scenario:**
        #. Create a vm without providing flist parameter, should fail.

        """
        self.log('Create a vm without providing flist parameter, should fail.')
        vm1_name = self.random_string()
        self.vms = {vm1_name: {}}
        self.temp_actions['vm']['service'] = vm1_name                                                            
        res = self.create_vm(vms=self.vms, temp_actions=self.temp_actions)
        self.assertEqual(res, "invalid input. Vm requires flist or ipxeUrl to be specifed.")
        self.log('%s ENDED' % self._testID)


class VM_actions(ZOS_BaseTest):
    def __init__(self, *args, **kwargs):
        super(VM_actions, self).__init__(*args, **kwargs)

    @classmethod
    def setUpClass(cls):
        self = cls()
        super(VM_actions, cls).setUpClass()
        cls.vm1_name = cls.random_string()
        cls.temp_actions = {
                             'vm': {'actions': ['install'], 'service': self.vm1_name}
                            }
        cls.vms = {cls.vm1_name: {'flist': self.vm_flist,
                                  'memory': 2048,
                                  'nics': [{'type': 'default', 'name': cls.random_string()}]}}

        res = self.create_vm(vms=cls.vms, temp_actions=cls.temp_actions)
        self.assertEqual(type(res), type(dict()))
        self.wait_for_service_action_status(cls.vm1_name, res[cls.vm1_name]['install'])
        cls.vm1_info = self.get_vm(cls.vm1_name)[0]
        vm_vnc_port = cls.vm1_info['vnc'] - 5900
        cls.vm_ip_vncport = '{}:{}'.format(self.zos_redisaddr, vm_vnc_port)

    @classmethod
    def tearDownClass(cls):
        self = cls()
        temp_actions = {'vm': {'actions': ['uninstall'], 'service': self.vm1_name}}
        if self.check_if_service_exist(self.vm1_name):
            res = self.create_vm(vms=self.vms, temp_actions=temp_actions)
            self.wait_for_service_action_status(self.vm1_name, res[self.vm1_name]['uninstall'])
        self.delete_services()

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
        self.log('%s STARTED' % self._testID)

        self.log('Pause [vm1], should succeed.')
        temp_actions = {'vm': {'actions': ['pause'], 'service': self.vm1_name}}
        res = self.create_vm(vms=self.vms, temp_actions=temp_actions)
        self.assertEqual(type(res), type(dict()))
        self.wait_for_service_action_status(self.vm1_name, res[self.vm1_name]['pause'])        
        
        self.log("Check that [vm1] has been paused successfully..")
        vms = self.zos_client.kvm.list()
        vm1 = [vm for vm in vms if vm['name'] == self.vm1_name]
        self.assertEqual(vm1[0]['state'], "paused")

        self.log("Resume [vm1], should succeed.")
        temp_actions = {'vm': {'actions': ['resume'], 'service': self.vm1_name}}
        res = self.create_vm(vms=self.vms, temp_actions=temp_actions)
        self.assertEqual(type(res), type(dict()))
        self.wait_for_service_action_status(self.vm1_name, res[self.vm1_name]['resume'])        
         
        self.log('Check that [vm1] is runninng ')
        vms = self.zos_client.kvm.list()
        vm1 = [vm for vm in vms if vm['name'] == self.vm1_name]
        self.assertEqual(vm1[0]['state'], "running")

        self.log('%s ENDED' % self._testID)

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
        self.log('%s STARTED' % self._testID)
        
        self.log('Shutdown [vm1], should succeed.')
        temp_actions = {'vm': {'actions': ['shutdown'], 'service': self.vm1_name, 'args': {'force':True}}}
        res = self.create_vm(vms=self.vms, temp_actions=temp_actions)
        self.assertEqual(type(res), type(dict()))
        self.wait_for_service_action_status(self.vm1_name, res[self.vm1_name]['shutdown'])        
        
        self.log("Check that [vm1] has been forced shutdown successfully..")
        time.sleep(10)
        vms = self.zos_client.kvm.list()
        vm1 = [vm for vm in vms if vm['name'] == self.vm1_name]
        self.assertFalse(vm1)

        self.log("Start [vm1], should succeed.")
        temp_actions = {'vm': {'actions': ['start'], 'service': self.vm1_name}}
        res = self.create_vm(vms=self.vms, temp_actions=temp_actions)
        self.assertEqual(type(res), type(dict()))
        self.wait_for_service_action_status(self.vm1_name, res[self.vm1_name]['start'])        

        self.log("Check that [vm1] is running again.")
        vms = self.zos_client.kvm.list()
        vm1 = [vm for vm in vms if vm['name'] == self.vm1_name]
        self.assertEqual(vm1[0]['state'], "running")

        self.log('%s ENDED' % self._testID)

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
        self.log('%s STARTED' % self._testID)
        
        self.log('Enable vnc_port for [vm1], should succeed.')
        temp_actions = {'vm': {'actions': ['enable_vnc'], 'service': self.vm1_name}}
        res = self.create_vm(vms=self.vms, temp_actions=temp_actions)
        self.assertEqual(type(res), type(dict()))
        self.wait_for_service_action_status(self.vm1_name, res[self.vm1_name]['enable_vnc'])        

        self.log("Check that vnc_port has been enabled successfully.")
        self.assertTrue(self.check_vnc_connection(self.vm_ip_vncport))

        self.log("Disable vnc_port for [vm1], should succeed.")
        temp_actions = {'vm': {'actions': ['disable_vnc'], 'service': self.vm1_name}}
        res = self.create_vm(vms=self.vms, temp_actions=temp_actions)
        self.assertEqual(type(res), type(dict()))
        self.wait_for_service_action_status(self.vm1_name, res[self.vm1_name]['disable_vnc'])        

        self.log("Check that vnc_port has been disabled successfully.")
        self.assertFalse(self.check_vnc_connection(self.vm_ip_vncport))

    @parameterized.expand(["reset", "reboot"])    
    @unittest.skip("https://github.com/threefoldtech/0-core/issues/35")
    def test004_reset_and_reboot_vm(self, action_type):
        """ ZRT-ZOS-008
        *Test case for testing reset vm*

        **Test Scenario:**

        #. Create a vm[vm1]  on node, should succeed.
        #. Enable vnc_port for [vm1], should succeed.
        #. Reset or reboot the vm, should suceeed.
        #. Check that [vm] has been rebooted/reset successfully.
        """
        self.log('%s STARTED' % self._testID)
        
        self.log("Create ssh container. ")
        cont1_name = self.random_string()
        temp_actions = {'container': {'actions': ['install'],'service': cont1_name}}
        containers = {cont1_name: {'hostname': cont1_name,
                                   'flist': 'https://hub.grid.tf/dina_magdy/ubuntu_1.flist',
                                   'storage': self.cont_storage,
                                   'nics': [{'type': 'default', 'name': self.random_string()}],
                                   'hostNetworking': True}}
        res = self.create_container(containers=containers, temp_actions=temp_actions)
        self.assertEqual(type(res), type(dict()))
        self.wait_for_service_action_status(cont1_name, res[cont1_name]['install'])

        conts = self.zos_client.container.list()
        (cont1_id, cont1) = [c for c in conts.items() if c[1]['container']['arguments']['name'] == cont1_name][0]
        ssh_client = self.zos_client.container.client(cont1_id)

        self.log('Enable vnc_port for [vm1], should succeed.')
        temp_actions = {'vm': {'actions': ['enable_vnc'], 'service': self.vm1_name}}
        res = self.create_vm(vms=self.vms, temp_actions=temp_actions)
        self.assertEqual(type(res), type(dict()))
        self.wait_for_service_action_status(self.vm1_name, res[self.vm1_name]['enable_vnc'])      

        self.log("%s the vm, should suceeed."%action_type)
        time.sleep(30)
        temp_actions = {'vm': {'actions': [action_type], 'service': self.vm1_name}}
        res = self.create_vm(vms=self.vms, temp_actions=temp_actions)
        self.assertEqual(type(res), type(dict()))
        self.wait_for_service_action_status(self.vm1_name, res[self.vm1_name][action_type])
        vm_ip = self.get_vm(self.vm1_name)[0]['default_ip']

        self.log("Check that [vm] has been %s successfully."%action_type)
        if action_type == 'reboot':        
            time.sleep(15)
        time.sleep(15)
        self.enable_ssh_access(self.vm_ip_vncport)
        response = self.execute_command_inside_vm(ssh_client, vm_ip, 'uptime')
        x = response.stdout.strip()
        uptime = int(x[x.find('up')+2:x.find('min')])
        self.assertEqual(response.state, 'SUCCESS')
        self.assertAlmostEqual(uptime, 0, delta=1)
