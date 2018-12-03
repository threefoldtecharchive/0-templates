from tests.testcases.base_test import BaseTest
from nose_parameterized import parameterized
import unittest
import time, random
@unittest.skip("https://github.com/threefoldtech/0-templates/issues/260")
class BridgeTestCases(BaseTest):
    def setUp(self):
        super().setUp()
        self.bridges = []
        self.containers = []

    def tearDown(self):
        for bridge in self.bridges:
            bridge.uninstall()
        self.bridges.clear()

        for container in self.containers:
            container.uninstall()
        self.containers.clear()
        super().tearDown()
        
    @parameterized.expand(['none', 'static', 'dnsmasq'])
    def test001_create_bridge(self, mode):
        """ ZRT-ZOS-030
        *Test case for creating bridge *

        **Test Scenario:**

        #. Create bridge (B1) with different modes, should succeed.
        #. Check that the params has been reflected correctly.
        """
        if mode == 'none':
            self.skipTest("https://github.com/threefoldtech/0-templates/issues/258")

        self.log('Create bridge (B1) with different modes, should succeed')
        bridge = self.controller.bridge_manager
        if mode == 'static':
            bridge.install(wait=True, mode=mode, settings={'cidr': '10.20.30.1/24'})
        elif mode == 'dnsmasq':
            bridge.install(wait=True, mode=mode, settings={"cidr": "10.20.30.1/24", "start": "10.20.30.2", "end": "10.20.30.3"})
        else:
            bridge.install(wait=True)
        self.bridges.append(bridge)

        self.log('Check that the params has been reflected correctly')
        nics = self.node.client.info.nic()
        nic = [nic for nic in nics if nic['name'] == bridge.default_data['name']]
        self.assertTrue(nic)
        addrs = [addr['addr'] for addr in nic[0]['addrs']][0]
        self.assertIn(bridge.default_data['settings']['cidr'], addrs)

    def test002_uninstall_bridge(self):
        """ ZRT-ZOS-031
        *Test case for uninstalling bridge *

        **Test Scenario:**

        #. Create bridge (B1) with basic params, should succeed.
        #. Check that bridge list, should be found.
        #. Unistall bridge (B1).
        #. Check that bridge list, should not be found.
        """
        self.log('Create bridge (B1) with basic params, should succeed')
        bridge = self.controller.bridge_manager
        bridge.install(wait=True, mode='static', settings={'cidr': '10.20.30.1/24'})

        self.log('Check that bridge list, should be found')
        bridge_list = self.node.client.bridge.list()
        self.assertIn(bridge.default_data['name'], bridge_list)

        self.log("Unistall bridge (B1).")
        bridge.uninstall()
        time.sleep(30)

        self.log("Check that bridge list, should not be found")
        bridge_list = self.node.client.bridge.list()
        self.assertNotIn(bridge.default_data['name'], bridge_list)

    def test003_create_bridge_with_hw_addr(self):
        """ ZRT-ZOS-032
        *Test case for creating bridge with specificed hardware address*

        **Test Scenario:**
        
        #. Create bridge (B1) with invalid hardware address, should fail.
        #. Create bridge (B2) with specificed hardware address, should succeed.
        #. Check that created bridge hardware address is reflected correctly.
        """
        self.log('Create bridge (B1) with invalid hardware address, should fail')
        hw_addr = self.random_string()
        bridge = self.controller.bridge_manager
        with self.assertRaises(Exception) as e:
            bridge.install(wait=True, hwaddr=hw_addr, mode='static', settings={'cidr': '10.20.30.1/24'})
        self.assertIn('hwAddr {} is not valid'.format(hw_addr), e.exception.args[0])

        self.log('Create bridge (B2) with specificed hardware address, should succeed')
        hw_addr = '32:64:7d:0b:c7:aa'
        bridge.install(wait=True, hwaddr=hw_addr, mode='static', settings={'cidr': '10.20.30.1/24'})
        self.bridges.append(bridge)

        self.log('Check that created bridge hardware address is reflected correctly')
        nics = self.node.client.info.nic()
        nic = [nic for nic in nics if nic['name'] == bridge.default_data['name']]
        self.assertTrue(nic)
        addr = nic[0]['hardwareaddr'] 
        self.assertIn(bridge.default_data['hwaddr'], addr)

    @unittest.skip("https://github.com/threefoldtech/0-core/issues/87")
    def test004_create_bridge_with_invalid_data(self):
        """ ZRT-ZOS-033
        *Test case for creating bridge with invalid data*

        **Test Scenario:**
        
        #. Create bridge (B1) with invalid mode, should fail.
        #. Create bridge (B2) with invalid cidr in static mode, should fail.
        #. Create bridge (B3) with invalid cidr in dnsmask mode, should fail.
        #. Create bridge (B4) with invalid ip range in dnsmask mode, should fail.
        """
        self.log('Create bridge (B1) with invalid mode, should fail.')
        bridge = self.controller.bridge_manager
        with self.assertRaises(Exception) as e:
            mode = self.random_string()
            bridge.install(wait=True, mode=mode)
        self.assertIn("mode must be one of 'none','static','dnsmasq'", e.exception.args[0])
        
        self.log('Create bridge (B2) with invalid cidr in static mode, should fail')
        with self.assertRaises(Exception) as e:
            mode = self.random_string()
            bridge.install(wait=True, mode='static', settings={'cidr': '10.1.10.2'})
        self.assertIn("invalid CIDR address: 10.1.10.2", e.exception.args[0])

        with self.assertRaises(Exception) as e:
            mode = self.random_string()
            bridge.install(wait=True, mode='static', settings={'cidr': '10.1.10.256/24'})
        self.assertIn("invalid CIDR address: 10.1.10.256/24", e.exception.args[0])

        with self.assertRaises(Exception) as e:
            mode = self.random_string()
            bridge.install(wait=True, mode='static', settings={'cidr': '10.10.25/24'})
        self.assertIn("invalid CIDR address: 10.10.25/24", e.exception.args[0])

        self.log('Create bridge (B3) with invalid cidr in dnsmask mode, should fail')
        with self.assertRaises(Exception) as e:
            mode = self.random_string()
            bridge.install(wait=True, mode='dnsmasq', settings={'cidr': '10.1.10.2', 'start': '10.10.1.10', 'end': '10.10.1.20'})
        self.assertIn("invalid CIDR address: 10.1.10.2", e.exception.args[0])

        with self.assertRaises(Exception) as e:
            mode = self.random_string()
            bridge.install(wait=True, mode='dnsmasq', settings={'cidr': '10.1.10.256/24', 'start': '10.10.1.10', 'end': '10.10.1.20'})
        self.assertIn("invalid CIDR address: 10.1.10.256/24", e.exception.args[0])

        with self.assertRaises(Exception) as e:
            mode = self.random_string()
            bridge.install(wait=True, mode='dnsmasq', settings={'cidr': '10.10.25/24', 'start': '10.10.1.10', 'end': '10.10.1.20'})
        self.assertIn("invalid CIDR address: 10.10.25/24", e.exception.args[0])

        self.log('Create bridge (B4) with invalid ip range in dnsmask mode, should fail')
        with self.assertRaises(Exception) as e:
            mode = self.random_string()
            bridge.install(wait=True, mode='dnsmasq', settings={'cidr': '10.10.1.1/24'})
        self.assertIn("start ip address out of range", e.exception.args[0])

        with self.assertRaises(Exception) as e:
            mode = self.random_string()
            bridge.install(wait=True, mode='dnsmasq', settings={'cidr': '10.10.1.1/24', 'start': '10.10.5.10', 'end': '10.10.1.20'})
        self.assertIn("start ip address out of range", e.exception.args[0])
        
        with self.assertRaises(Exception) as e:
            mode = self.random_string()
            bridge.install(wait=True, mode='dnsmasq', settings={'cidr': '10.10.1.1/24', 'start': '10.10.1.10', 'end': '10.1.1.20'})
        self.assertIn("end ip address out of range", e.exception.args[0])
        
        with self.assertRaises(Exception) as e:
            mode = self.random_string()
            bridge.install(wait=True, mode='dnsmasq', settings={'cidr': '10.10.1.1/24', 'start': '10.10.1.256', 'end': '10.10.1.20'})
        self.assertIn("invalid IP address: 10.10.1.256", e.exception.args[0])
    
        with self.assertRaises(Exception) as e:
            mode = self.random_string()
            bridge.install(wait=True, mode='dnsmasq', settings={'cidr': '10.10.1.1/24', 'start': '10.10.1.25', 'end': '10.10.1.256'})
        self.assertIn("invalid IP address: 10.10.1.256", e.exception.args[0])

        with self.assertRaises(Exception) as e:
            mode = self.random_string()
            bridge.install(wait=True, mode='dnsmasq', settings={'cidr': '10.10.1.1/24', 'start': '10.1.25', 'end': '10.10.1.20'})
        self.assertIn("invalid IP address: 10.1.25", e.exception.args[0])

        with self.assertRaises(Exception) as e:
            mode = self.random_string()
            bridge.install(wait=True, mode='dnsmasq', settings={'cidr': '10.10.1.1/24', 'start': '10.10.1.25', 'end': '10.1.20'})
        self.assertIn("invalid IP address: 10.1.20", e.exception.args[0])

        with self.assertRaises(Exception) as e:
            mode = self.random_string()
            bridge.install(wait=True, mode='dnsmasq', settings={'cidr': '10.10.1.1/24', 'start': '10.1..25', 'end': '10.10.1.20'})
        self.assertIn("invalid IP address: 10.1..25", e.exception.args[0])

        with self.assertRaises(Exception) as e:
            mode = self.random_string()
            bridge.install(wait=True, mode='dnsmasq', settings={'cidr': '10.10.1.1/24', 'start': '10.10.1.25', 'end': '10.1..20'})
        self.assertIn("invalid IP address: 10.1..20", e.exception.args[0])

        with self.assertRaises(Exception) as e:
            mode = self.random_string()
            bridge.install(wait=True, mode='dnsmasq', settings={'cidr': '10.10.1.1/24', 'start': '10.10.1.50', 'end': '10.10.1.20'})
        self.assertIn("mode must be one of 'none','static','dnsmasq'", e.exception.args[0])

    @unittest.skip("https://github.com/threefoldtech/0-templates/issues/258")
    def test003_add_remove_list_nics_for_bridge(self):
        """ ZRT-ZOS-034
        *Test case for adding, removing and listing nics for a bridges*

        **Test Scenario:**
        #. Create bridge (B1), should succeed.
        #. List B1 nics, should be empty.
        #. Create an nic (N1) for core0, should succeed.
        #. Add nic (N1) to bridge (B1), should succeed.
        #. List B1 nics, N1 should be found.
        #. Remove N1 from bridge nics, should succed.
        #. Remove N1 from core0, should succeed.
        """
        self.log('Create bridge (B1), should succeed')
        cidr = "20.20.30.1/24"
        bridge = self.controller.bridge_manager
        bridge.install(wait=True, mode='static', settings={"cidr": cidr})
        self.bridges.append(bridge)

        self.log("List B1 nics, should be empty")
        nic_list = bridge.nic_list()
        self.assertFalse(nic_list)

        self.log('Create an nic (N1) for core0, should succeed')
        nic_name = self.random_string()
        self.node.client.bash('ip link add {} type dummy'.format(nic_name)).get()
        nic = [n for n in self.node.client.info.nic() if n['name'] == nic_name]
        self.assertTrue(nic)

        self.log("Add nic (N1) to bridge (B1), should succeed")
        bridge.nic_add(nic_name)

        self.log("List B1 nics, N1 should be found")
        nic_list = bridge.nic_list()
        self.assertTrue(nic_list)

        self.log("Remove N1, should succed")
        bridge.nic_remove(nic_name)
        
        self.log("List B1 nics, should be empty")
        nic_list = bridge.nic_list()

        self.log("Remove N1 from core0, should succeed")
        self.node.client.bash('ip link delete {} type dummy'.format(nic_name)).get()
    
    @parameterized.expand(["True", "False"])
    def test005_create_bridges_with_nat_parameter(self, nat):
        """ ZRT-ZOS-035
        *Test case for creating bridge with nat paramter*

        **Test Scenario:**
        
        #. Create bridge (B1) with nat = False/True, should succeed.
        #. Create container (C1) and attach bridge (B1) to it, should succeed.
        #. Add ip to eth0 and set it up, should succeed.
        #. set network interface eth0 as default route, should succeed.
        #. Try to ping 8.8.8.8 when NAT is enabled, should succeed.
        #. Try to ping 8.8.8.8 when NAT is disabled, should fail.
        """
        self.log('Create bridge (B1) with nat = False/True, should succeed')
        cidr = "10.1.0.1/24"
        bridge = self.controller.bridge_manager
        if nat == "True":
            bridge.install(wait=True, mode='static', settings={"cidr": cidr}, nat=True)
        else:
            bridge.install(wait=True, mode='static', settings={"cidr": cidr}, nat=False)
        self.bridges.append(bridge)

        self.log('Create container (C1) and attach bridge (B1) to it, should succeed.')
        nic = [{'type': 'bridge', 'id': bridge.default_data['name']}]
        container = self.controller.container_manager(parent=self.controller, service_name=None)
        container.install(wait=True, nics=nic, privileged=True)
        self.containers.append(container)
        conts = self.node.containers.list()
        cont = [c for c in conts if container.data['hostname'] in c.hostname][0]
        self.node.client.container.nic_remove(cont.id, 1) # remove the default nic as containers can reach each other through it

        self.log('Add ip to eth0 and set it up')
        response = cont.client.system('ip a a 10.1.0.2/24 dev eth0').get()
        self.assertEqual(response.state, 'SUCCESS', response.stderr)
        response = cont.client.bash('ip l s eth0 up').get()
        self.assertEqual(response.state, 'SUCCESS', response.stderr)

        self.log('set network interface eth0 as default route, should succeed')
        response = cont.client.bash('ip route add default dev eth0 via 10.1.0.1').get()
        self.assertEqual(response.state, 'SUCCESS', response.stderr)

        if nat == "True":
            self.log('Try to ping 8.8.8.8 when NAT is enabled, should succeed')
            response = cont.client.bash('ping -w3 8.8.8.8').get()
            self.assertEqual(response.state, 'SUCCESS', response.stderr)
        else:
            self.log('Try to ping 8.8.8.8 when NAT is disabled, should fail')
            response = cont.client.bash('ping -w3 8.8.8.8').get()
            self.assertEqual(response.state, 'ERROR', response.stderr)
    
    def test006_attach_bridge_to_three_containers(self):
        """ ZRT-ZOS-036
        *Test case for attach bridge to three containers*

        **Test Scenario:**
        
        #. Create bridge (B1) with dnsmasq mode (cidr (CIDR1) and 2 ip range), should succeed.
        #. Create 3 containers C1, C2, C3 with bridge (B1), should succeed.
        #. Check if each container (C1), (C2) got an ip address, should be found.
        #. Check if container (C3) got an ip address, should not be found.
        #. Check if each container (C1), (C2) can reach each other, should succeed.
        #. Check if container (C3) can reach the other containers, should fail.
        """
        self.log('Create bridge (B1) with dnsmasq mode (cidr (CIDR1) and 2 ip range), should succeed')
        cidr = "20.20.30.1/24"
        ip_range = ["20.20.30.2", "20.20.30.3"]
        bridge = self.controller.bridge_manager
        bridge.install(wait=True, mode='dnsmasq', settings={"cidr": cidr, "start": ip_range[0], "end": ip_range[1]})
        self.bridges.append(bridge)

        self.log('Create 3 containers C1, C2, C3 with bridge (B1), should succeed')
        nic = [{'type': 'bridge', 'id': bridge.default_data['name'], 'config': {'dhcp': True}}]
        for c in range(3):
            container = self.controller.container_manager(parent=self.controller, service_name=None)
            container.install(wait=True, nics=nic)
            self.containers.append(container)

        for container in self.containers:
            self.log("Check container nics, bridge (B1) should be attached.")
            conts = self.node.containers.list()
            cont = [c for c in conts if container.data['hostname'] in c.hostname][0]
            self.node.client.container.nic_remove(cont.id, 1) # remove the default nic as containers can reach each other through it
            nics = cont.client.info.nic()
            nic = [nic for nic in nics if nic['name'] == 'eth0']
            self.assertTrue(nic)
            addrs = [addr['addr'] for addr in nic[0]['addrs'] if addr['addr'][:addr['addr'].find('/')] in ip_range]

            if container == self.containers[2]:
                self.log("Check if container (C3) got an ip address, should not be found.")
                self.assertFalse(addrs)

                self.log("Check if container (C3) can reach the other containers, should fail")
                response = cont.client.bash('ping {} -w5'.format(ip_range[0])).get()
                self.assertEqual(response.state, 'ERROR', response.stderr.strip())
            else:
                self.log("Check if each container (C1), (C2) got an ip address, should be found.")
                self.assertTrue(addrs)

                self.log("Check if each container (C1), (C2) can reach each other, should succeed")
                addrs = addrs[0][:addrs[0].find('/')]
                addrs2 = ip_range[0] if addrs == ip_range[1] else ip_range[1]
                response = cont.client.bash('ping {} -w5'.format(addrs2)).get()
                self.assertEqual(response.state, 'SUCCESS', response.stderr.strip())