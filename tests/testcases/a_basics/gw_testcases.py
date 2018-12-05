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
        gateway = self.controller.gw_manager(parent=self.controller)
        with self.assertRaises(Exception) as e:
            gateway.install(wait=True, networks=network)
        self.assertEqual("Need exactly one public network", e.exception.args[0])

        self.log('Create gateways[GW1] with public default network, should succeed.')
        network[0]['public'] = True
        gateway.install(wait=True, networks=network)
        self.gws.append(gateway)
    
    def test002_add_network_name_exist(self):
        """ZRT-ZOS-022
        *Test case for adding network to gateway with same name.
        Test Scenario:

        #. Create gateways[GW1] with public default network, should succeed.
        #. Add network [N1] with same type and same name to [GW1], should fail.
        #. Add network [N2] with different type and same name to [GW1], should fail.
        """
        self.log("Create gateways[GW1] with public default network, should succeed.")
        gateway = self.controller.gw_manager(parent=self.controller)
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

    @unittest.skip('https://github.com/threefoldtech/0-templates/issues/218')
    def test003_add_zerotier_network(self):
        """ZRT-ZOS-023
        *Test case for adding zerotier network to gateway .
        Test Scenario:

        #. Create gateways[GW1] with public default network, should succeed.
        #. Add zerotier network to gateway[GW1].
        #. Get zerotier identity.
        #. Check that zerotier network is added successfully to gateway[GW1].
        """
        self.log("Create gateways[GW1] with public default network, should succeed.")
        gateway = self.controller.gw_manager(parent=self.controller)
        gateway.install(wait=True)
        self.gws.append(gateway)

        zt_client = self.controller.zt_client(self.controller)
        zt_network = {'name': self.random_string(), 'type': 'zerotier', 'id': self.zt_id, 'ztClient': zt_client.service_name, 'public': False}
        gateway.add_network(network=zt_network)

        self.log('Get zerotier identity.')
        conts = self.node.containers.list()
        cont = [c for c in conts if gateway.default_data['hostname'] in c.hostname][0]
        identity = cont.identity

        self.log('Check that zerotier network is added successfully to gateway[GW1].')
        gw_zt_ip = self.get_zerotier_ip(identity)
        self.assertTrue(gw_zt_ip)
    
    def test004_remove_network(self):
        """ZRT-ZOS-024
        *Test case for removing network from gateway .
        Test Scenario:

        #. Create gateways[GW1] with public default network and private zerotier network, should succeed.
        #. Remove the public default network, should fail. 
        #. Remove zerotier network, should succeed
        """
        self.log("Create gateways[GW1] with public default network, should succeed.")
        gateway = self.controller.gw_manager(parent=self.controller)
        zt_client = self.controller.zt_client(self.controller)
        zt_network = {'name': self.random_string(), 'type': 'zerotier', 'id': self.zt_id, 'ztClient': zt_client.service_name, 'public': False}
        default_network = {'name': 'nat0', 'type': 'default', 'public': True, 'id': ''}
        gateway.install(wait=True, networks=[default_network, zt_network])
        self.gws.append(gateway)
        
        self.log('Check that default network and zerotier network are added')
        info = gateway.info().result
        self.assertEqual(len(info['networks']), 2)

        self.log("Remove the public default network, should fail.")
        with self.assertRaises(Exception) as e:
            gateway.remove_network(default_network['name'])
        self.assertIn("Need exactly one public network", e.exception.args[0])

        self.log('Remove zerotier network, should succeed')
        gateway.remove_network(name=zt_network['name'])
        info = gateway.info().result
        self.assertEqual(len(info['networks']), 1)
        self.assertNotEqual(info['networks'][0]['type'], 'zerotier')

    def test005_deploy_getways_with_same_default_public_network(self):
        """ZRT-ZOS-025
        *Test case for deploying more than one gateway with default public network .
        Test Scenario:

        #. Create gateways[GW1] with public default network, should succeed.
        #. Create gateways[GW2] with public default network, should fail.
        """
        self.log("Create gateways[GW1] with public default network, should succeed.")
        gateway1 = self.controller.gw_manager(parent=self.controller)
        gateway1.install(wait=True)
        self.gws.append(gateway1)

        self.log("Create gateways[GW2] with public default network, should fail.")
        gateway2 = self.controller.gw_manager(parent=self.controller)
        with self.assertRaises(Exception) as e:
            gateway2.install(wait=True)
        self.assertIn("port already in use",e.exception.args[0])
        self.gws.append(gateway2)

    @unittest.skip("https://github.com/threefoldtech/0-templates/issues/226")
    def test006_create_gateway_with_port_forward(self):
        """ZRT-ZOS-026
        *Test case for creating gateway with port forward
        Test Scenario:

        #. Make network[N1] has default network as public and zerotier network as private.
        #. Create vm[vm1] with zerotier network, should succeed.
        #. Start server on [P1], should succeed.
        #. Make port forward[P2] from public default network to vm[VM1]'s port[P1].
        #. Create gateways[GW1] with network[N1] and port forword[P2].
        #. Try to access the vm server through the port forward[P2].
        """
        self.log('Make network[N1] has default network as public and zerotier network as private.')
        zt_client = self.controller.zt_client(self.controller)
        network = [{'name': 'zerotier_nic', 'type': 'zerotier', 'id': self.zt_id, 'ztClient': zt_client.service_name, 'public': False},
                   {'name': 'nat0', 'type': 'default', 'public': True, 'id': ''}]
        
        self.log('Create vm[vm1] with zerotier network, should succeed.')
        ssh_config = [{'path': '/root/.ssh/authorized_keys', 'content': self.ssh_key, 'name': 'sshkey'}]
        vm = self.controller.vm_manager
        vm.install(wait=True, configs=ssh_config, nics=network)
        self.vms.append(vm)
        ssh_port = int(vm.info().result['ports'].popitem()[0])

        self.log('Start server on [P1], should succeed.')
        host_port = random.randint(3000, 4000)
        guest_port = random.randint(2000, 3000)
        cmd = 'python3 -m http.server {} &> /tmp/server.log &'.format(guest_port)
        self.ssh_vm_execute_command(vm_ip=self.node_ip, port=ssh_port, cmd=cmd)
        time.sleep(10)        

        self.log("Make port forward[P2] from public default network to vm[VM1]'s port[P1].")
        vm_zt_ip = self.get_vm_zt_ip(vm)
        portforward = [{'protocols': ['tcp'], 'srcport': host_port, 'srcnetwork': 'nat0', 'dstip': vm_zt_ip, 'dstport': guest_port, 'name': 'myport'}]

        self.log("Create gateways[GW1] with network[N1] and port forword[P2].")
        gateway = self.controller.gw_manager(parent=self.controller)
        gateway.install(wait=True, networks=network, portforwards=portforward)
        self.gws.append(gateway)

        self.log("Try to access the vm server through the port forward[P2]")
        response = requests.get('http://{}:{}/.ssh/authorized_keys'.format(self.node_ip, host_port))
        content = response.content.decode('utf-8')

        self.log("Make sure that ssh key is in the authorized_key")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(content, self.ssh_key)

    @unittest.skip('https://github.com/threefoldtech/0-templates/issues/218')
    def test007_stop_and_start_gateway(self):
        """ZRT-ZOS-027
        *Test case for stopping and starting gateway .
        Test Scenario:

        #. Create gateways[GW1] with public default network, should succeed.
        #. Make sure gateway container is created.
        #. Stop gateway[GW1] and make sure that it stopped successfully.
        #. Start it again and make sure that it started successfully.
        """
        self.log("Create gateways[GW1] with public default network, should succeed.")
        gateway = self.controller.gw_manager(parent=self.controller)
        gateway.install(wait=True)
        self.gws.append(gateway)

        self.log('Make sure gateway container is created.')
        conts = self.node.containers.list()
        cont = [c for c in conts if gateway.default_data['hostname'] in c.hostname]
        self.assertTrue(cont)

        self.log("Stop gateway[GW1] and make sure that it stopped successfully.")
        gateway.stop()
        conts = self.node.containers.list()
        cont = [c for c in conts if gateway.default_data['hostname'] in c.hostname]
        self.assertFalse(cont)

        self.log("Start it again and make sure that it started successfully.")
        gateway.start()
        conts = self.node.containers.list()
        cont = [c for c in conts if gateway.default_data['hostname'] in c.hostname]
        self.assertTrue(cont)