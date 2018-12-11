from tests.testcases.base_test import BaseTest
import unittest


class NodeTestcases(BaseTest):

    def setUp(self):
        super().setUp()
        self.node_tem = self.controller.node_manager

    def test001_get_node_info(self):
        """ ZRT-ZOS-039
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

    def test002_get_node_stats(self):
        """ ZRT-ZOS-040
        *Test case for getting node statistics *

        **Test Scenario:**

        #. Get node_service statistics, should succeed.
        #. Check that the node_service statistics is the same as that of the node.
        """

        self.log('Get node_service statistics, should succeed.')
        ser_stats = self.node_tem.stats()
        self.assertTrue(ser_stats)

        self.log('Check that the node_service statistics is the same as that of the node')
        node_stats = self.node.client.aggregator.query()
        self.assertEqual(len(ser_stats.result), len(node_stats))

    def test003_get_node_processes(self):
        """ ZRT-ZOS-041
        *Test case for getting node processes *

        **Test Scenario:**

        #. Get node_service processes, should succeed.
        #. Check that the node_service processes is the same as that of the node.
        """

        self.log('Get node_service processes, should succeed.')
        ser_processes = self.node_tem.processes()
        self.assertTrue(ser_processes)

        self.log('Check that the node_service processes is the same as that of the node')
        node_processes = self.node.client.process.list()
        self.assertEqual(len(ser_processes.result), len(node_processes))

    def test004_get_node_os_version(self):
        """ ZRT-ZOS-042
        *Test case for getting node os version *

        **Test Scenario:**

        #. Get node_service os_version, should succeed.
        #. Check that the node_service os version is the same as that of the node.
        """

        self.log('Get node_service os version, should succeed.')
        ser_os_version = self.node_tem.os_version()
        self.assertTrue(ser_os_version)

        self.log('Check that the node_service os version is the same as that of the node')
        node_os_version = self.node.client.ping()[13:].strip()
        self.assertEqual(ser_os_version.result, node_os_version)
