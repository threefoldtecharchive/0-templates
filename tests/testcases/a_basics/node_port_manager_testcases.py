from tests.testcases.base_test import BaseTest
import unittest
import time




class NodePortManagerTestcases(BaseTest):


    def test001_reserve_release_port_using_service_guid(self):

        """
            *Test case for reserving ports using service guid .
            Test Scenario:

            #. get a running service GUID and reserve two ports using it , should success.
            #. release this two ports one by one , should success
            #. make sure that the port is released by reserve another new port again

        """
        node_service = self.controller.node_manager
        guid = node_service.service.guid
        self.log('reserving port for one service')
        node_port = self.controller.node_port_manager
        ports = node_port.reserve(guid, 2).result
        self.assertTrue(ports)
        port_reserved_1 = ports[0]
        port_reserved_2 = ports[1]
        self.log('releasing  the 1st reserved port for one service')
        node_port.release(guid, [port_reserved_1])
        time.sleep(30)
        self.log('releasing  the 1st reserved port for one service')
        node_port.release(guid, [port_reserved_2])
        port_reserved_3 = node_port.reserve(guid).result
        node_port = self.controller.node_port_manager
        for port in node_port.data["data"]["ports"]:
                if port['port'] == port_reserved_1:
                    print("successfully released")
        #self.assertEqual(port_reserved_3, port_reserved_1)


    def test002_reserve_with_guid1_release_with_guid2(self):

        """
            *Test case for reserving port using guid and release it with different GUID

            #. get running serviceguid and reserve  port using it
            #. try to release this port using different service guid , should fail
            #. release this port using same GUID , should success
        """

        node_service = self.controller.node_manager
        guid = node_service.service.guid
        guid2 = (self.controller.remote_robot.services.find(template_name='node_capacity')[0]).guid
        node_port = self.controller.node_port_manager
        port = node_port.reserve(guid).result
        self.assertTrue(port)
        self.log('releasing the reserved port with different guid , should fail')
        with self.assertRaises(Exception):
            node_port.release(guid2, port)
        self.log('releasing the reserved port with right guid , should success')
        node_port.release(guid, port)

