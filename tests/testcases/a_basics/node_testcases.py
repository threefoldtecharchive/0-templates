from tests.testcases.base_test import BaseTest
from Jumpscale import j
import unittest
import time, random

class NodeTestcases(BaseTest):
    def setUp(self):
        super().setUp()
        self.node_tem = self.controller.node_manager

    def test001_get_node_info(self):
        """ ZRT-ZOS-000
        *Test case for getting node info *

        **Test Scenario:**

        #. Get node_service info, should succeed.
        #. Check that the node_service info is the same as the node info.
        """

        self.log('Get node_service info, should succeed')
        ser_info = self.node_tem.info()
        self.assertTrue(ser_info)

        self.log('Check that the node_service info is the same as the node info.')
        node_info = self.node.client.info.os()
        for key in node_info.keys():
            self.assertAlmostEqual(node_info[key], ser_info.result[key], delta=10)
