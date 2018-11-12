from tests.testcases.base_test import BaseTest
from nose_parameterized import parameterized
import unittest
import time, random

class GWTests(BaseTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gws = []

    def tearDown(self):
        for gw in self.gws:
            gw.stop()
        self.gws.clear()
        super().tearDown()
        
    def test001_deploy_getway_with_without_public_network(self):
        """ ZRT-ZOS-011
        *Test case for deploying gateway with/without default public network .
        Test Scenario:

        #. Create gateways[GW1] without public default network, should fail.
        #. Create gateways[GW1] with public default network, should succeed.
        """
        self.log('Create gateways[GW1] without public default network, should fail.')
        network = [{'name': 'public_nic', 'type': 'default', 'public': False}]
        gateway = self.controller.gw_manager(parent=self.controller, service_name=None)
        with self.assertRaises(Exception) as e:
            gateway.install(wait=True, networks=network)
        self.assertEqual("Need exactly one public network", e.exception.args[0])

        self.log('Create gateways[GW1] with public default network, should succeed.')
        network = [{'name': 'public_nic', 'type': 'default', 'public': True}]
        gateway.install(wait=True, networks=network)
        self.gws.append(gateway)
    
    def test002_add_network_name_exist(self):
        """ZRT-ZOS-012
        *Test case for deploying gateway with default public network .
        Test Scenario:

        #. Create gateways[GW1] with public default network, should succeed.
        #. Add network [N1] with same type and same name to [GW1], should fail.
        #. Add network [N2] with different type and same name to [GW1], should fail.
        """
        self.log("Create gateways[GW1] with public default network, should succeed.")
        gateway = self.controller.gw_manager(parent=self.controller, service_name=None)
        gateway.install(wait=True)
        self.gws.append(gateway)
        
        self.log("Add network [N1] with same type and same name to [GW1], should fail.")
        network = {'name': "public_nic", 'type': "default", 'id': ''}
        with self.assertRaises(Exception) as e:
            gateway.add_network(network=network)
        # self.assertEqual("Network with name public_nic already exists", e.exception.args[0])

        self.log("Add network [N2] with different type and same name to [GW1], should fail.")
        network = {'name': "public_nic", 'type': "zerotier"}
        with self.assertRaises(Exception) as e:
            gateway.add_network(network=network)
        # self.assertIn("Network with name public_nic already exists", e.exception.args[0])        

    def test003_remove_network(self):
        """ZRT-ZOS-013
        *Test case for deploying gateway with default public network .
        Test Scenario:

        #. Create gateways[GW1] with public default network, should succeed.
        #. Remove the public default network, should succeed. 
        #. Check that network has been removed.
        """
        self.log("Create gateways[GW1] with public default network, should succeed.")
        gateway = self.controller.gw_manager(parent=self.controller, service_name=None)
        gateway.install(wait=True)
        self.gws.append(gateway)

        self.log("Remove the public default network, should succeed.")
        with self.assertRaises(Exception) as e:
            gateway.remove_network('public_nic')
        self.assertIn("Need exactly one public network", e.exception.args[0])

    def test004_deploy_getways_with_public_network(self):
        """ZRT-ZOS-014
        *Test case for deploying more than one gateway with default public network .
        Test Scenario:

        #. Create gateways[GW1] with public default network, should succeed.
        #. Create gateways[GW2] with public default network, should fail.
        """
        self.log("Create gateways[GW1] with public default network, should succeed.")
        gateway1 = self.controller.gw_manager(parent=self.controller, service_name=None)
        gateway1.install(wait=True)
        self.gws.append(gateway1)

        self.log("Create gateways[GW2] with public default network, should fail.")
        gateway2 = self.controller.gw_manager(parent=self.controller, service_name=None)
        with self.assertRaises(Exception) as e:
            gateway2.install(wait=True)
        self.assertIn("port already in use",e.exception.args[0])
        self.gws.append(gateway2)

    # def test05_create_gateway_with_public_and_zerotier_vm(self):
    #     """ZRT-ZOS-015
    #     *Test case for deploying gateways with public and zerotier networks. *
    #     Test Scenario:

    #     #. Create gateway with public default network, should succeed.
    #     #. Add zerotier network as private network, should succeed.
    #     #. Adding a new vm t to gateway private network , should succeed.
    #     #. Check that the vm has been join the zerotier network.
    #     """
    #     gateway = self.controller.gw_manager(parent=self.controller, service_name=None)
    #     gateway.install(wait=True)

    #     self.log("Add zerotier network as private network, should succeed.")
    #     network = [{'name': 'zt_nic', 'type': 'zerotier', 'id':}]
    #     gateway.add_network()

    #     self.log("Adding a new vm t to gateway private network , should succeed.")
    #     self.vm.install()
    #     self.vms.append(self.vm.info()['uuid'])
    #     zt_network.hosts.add(self.vm.vm_sal)
    #     self.gateway.install()
    #     self.vm.install()

    #     self.log("Check that the vm has been join the zerotier network.")
    #     ztIdentity = self.vm.data["ztIdentity"]
    #     vm_zt_ip = self.get_zerotier_ip(ztIdentity)
    #     result = self.ssh_vm_execute_command(vm_ip=vm_zt_ip, cmd='pwd')
    #     self.assertNotEqual(len(result), 0)