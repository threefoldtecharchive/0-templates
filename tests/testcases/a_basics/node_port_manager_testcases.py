from tests.testcases.base_test import BaseTest
from uuid import uuid4
import unittest
import random





class NodePortManagerTestcases(BaseTest):


    def test001_reserve_release_port_using_service_guid(self):

        """
            *Test case for reserving ports using service guid .
            Test Scenario:

            #. Create random service GUID and reserve two ports using it , should success.
            #. release this two ports one by one , should success
            #. make sure that the port is released by reserve another new port again

        """
        guid = str(uuid4())
        self.log('reserving port for one service')
        node_port_service = self.controller.node_port_manager
        ports = node_port_service.reserve(guid, 2).result
        self.assertTrue(ports)
        port_reserved_1 = ports[0]
        port_reserved_2 = ports[1]
        self.log('releasing  the 1st reserved port for one service')
        node_port_service.release(guid, port_reserved_1)
        self.log('releasing  the 1st reserved port for one service')
        node_port_service.release(guid, port_reserved_2)
        port_reserved_3 = node_port_service.reserve(guid).result
        self.assertEqual(port_reserved_3, port_reserved_1)


    def test002_reserve_with_guid1_release_with_guid2(self):

        """
            *Test case for reserving port using guid and release it with different GUID

            #. Create guid and reserve  port using it
            #. try to release this port using different guid , should fail
            #. release this port using same GUID , should success
        """
        guid = str(uuid4())
        guid2 = str(uuid4())
        node_port_service = self.controller.node_port_manager
        port = node_port_service.reserve(guid).result
        self.assertTrue(port)
        self.log('releasing the reserved port with different guid , should fail')
        with self.assertRaises(Exception):
            node_port_service.release(guid2, port)
        self.log('releasing the reserved port with right guid , should success')
        node_port_service.release(guid, port)

