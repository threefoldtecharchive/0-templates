from tests.testcases.base_test import BaseTest
import unittest


class NodePortManagerTestcases(BaseTest):

    def test001_reserve_release_port_using_service_guid(self):
        """ZRT-ZOS-050
        *Test case for reserving and releasing ports using service guid.
        Test Scenario:

        #. get a running service GUID and reserve two ports using it, should success.
        #. make sure that this two ports is reserved, should success.
        #. release this two ports, should success.
        #. make sure that the port is released by checking that it's not in reserved ports.
        """
        self.log('get a running service GUID and reserve two ports using it, should success')
        node = self.controller.node_manager
        guid = node.service.guid
        node_port = self.controller.node_port_manager
        ports = node_port.reserve(guid, 2).result
        self.assertTrue(ports)
        port_reserved_1 = {'serviceGuid': guid, 'port': ports[0]}
        port_reserved_2 = {'serviceGuid': guid, 'port': ports[1]}

        self.log("make sure that this two ports is reserved, should success.")
        ports_data = node_port.service.data["data"]["ports"]
        self.assertIn(port_reserved_1, ports_data)
        self.assertIn(port_reserved_2, ports_data)

        self.log('release this two ports, should success')
        node_port.release(guid, ports)

        self.log("make sure that the port is released by checking that it's not in reserved ports.")
        ports_data = node_port.service.data["data"]["ports"]
        self.assertNotIn(port_reserved_1, ports_data)
        self.assertNotIn(port_reserved_2, ports_data)

    def test002_reserve_with_guid1_release_with_guid2(self):
        """ZRT-ZOS-051
        *Test case for reserving port using guid and release it with different GUID
        Test Scenario:

        #. get running service guid and reserve port using it.
        #. try to release this port using different service guid, should fail.
        #. release this port using right GUID, should success.
        """
        self.log('get running service guid and reserve port using it')
        node = self.controller.node_manager
        guid = node.service.guid
        guid2 = (self.controller.remote_robot.services.find(template_name='node_capacity')[0]).guid
        node_port = self.controller.node_port_manager
        port = node_port.reserve(guid).result
        self.assertTrue(port)

        self.log('try to release this port using different service guid, should fail')
        with self.assertRaises(Exception):
            node_port.release(guid2, port)

        self.log('release this port using right GUID, should success')
        node_port.release(guid, port)
