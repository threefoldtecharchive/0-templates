from tests.testcases.base_test import BaseTest
from nose_parameterized import parameterized
import unittest, requests
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
        """ ZRT-ZOS-021
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
        network[0]['public'] = True
        gateway.install(wait=True, networks=network)
        self.gws.append(gateway)
    
    @unittest.skip("https://github.com/threefoldtech/0-templates/issues/211")
    def test002_add_network_name_exist(self):
        """ZRT-ZOS-022
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
        self.assertEqual("Network with name public_nic already exists", e.exception.args[0])

        self.log("Add network [N2] with different type and same name to [GW1], should fail.")
        network = {'name': "public_nic", 'type': "zerotier"}
        with self.assertRaises(Exception) as e:
            gateway.add_network(network=network)
        self.assertIn("Network with name public_nic already exists", e.exception.args[0])        

    def test003_remove_network(self):
        """ZRT-ZOS-023
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
        """ZRT-ZOS-024
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
