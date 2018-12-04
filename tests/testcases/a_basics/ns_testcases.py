from tests.testcases.base_test import BaseTest
from nose_parameterized import parameterized
from jumpscale import j
import unittest
import time, random
import itertools

items = [['user', 'seq', 'direct'],
         ['yes', 'no'],
         ['hdd', 'ssd']]
para_list = list(itertools.product(*items))

class NSTestCases(BaseTest):  
    def tearDown(self):
        self.ns.uninstall()
        super().tearDown()

    def find_namespace_in_list(self, zdb, ns_name):
        ns_list = zdb.schedule_action('namespace_list').wait(die=True).result
        for ns in ns_list:
            if ns['name'] == ns_name:
                return True
        else:
            return False

    @parameterized.expand(para_list)
    def test001_create_namespace(self, mode, public, disk_type):
        """ ZRT-ZOS-028
        *Test case for creating namespace *

        **Test Scenario:**

        #. Create namespace (NS) with different params, should succeed.
        #. Check that the params has been reflected correctly.
        """
        self.log('Create namespace (NS) with basic params, should succeed')
        self.ns = self.controller.ns_manager
        if public == 'yes':
            self.ns.install(wait=True, mode=mode, diskType=disk_type, public=True)
        else:
            self.ns.install(wait=True, mode=mode, diskType=disk_type)

        self.log('Prepare data for testing')
        info = self.ns.info().result
        if mode == 'user':
            mode = 'userkey'
        else:
            mode = 'sequential'
        url = self.ns.private_url().result
        d_type, zdb_ser_name = self.get_namespace_disk_type(url)

        self.log('Check that the params has been reflected correctly.')
        self.assertEqual(info['mode'], mode)
        self.assertEqual(info['data_limits_bytes']/1024**3, self.ns.default_data['size'])
        self.assertEqual(d_type, disk_type)
        self.assertEqual(info['public'], public)

    def test002_uninstall_namespace_with_zdb(self):
        """ ZRT-ZOS-029
        *Test case for uninstalling namespace *

        **Test Scenario:**

        #. Create namespace (NS1) with basic params, should succeed.
        #. Get the zdb that namespace (NS1) has been created on.
        #. Check that namesapce (NS1) in namespace list, should be found.
        #. Uninstall namespace (NS1). 
        #. Check that namespace (NS1) in namespace list, should not be found.
        """
        self.log('Create namespace (NS1) with basic params, should succeed.')
        self.ns = self.controller.ns_manager
        self.ns.install(wait=True)

        self.log("Get the zdb that namespace (NS1) has been created on")
        url = self.ns.private_url().result
        d_type, zdb_ser_name = self.get_namespace_disk_type(url)
        robot_name = self.random_string()
        j.clients.zrobot.get(robot_name, data={'url': self.config['robot']['remote_server']})
        robot = j.clients.zrobot.robots[robot_name]
        robot = self.robot_god_token(self.controller.remote_robot)
        zdb = robot.services.get(name=zdb_ser_name)

        self.log('Check that namesapce (NS1) in namespace list, should be found.')
        ns_found = self.find_namespace_in_list(zdb, self.ns.default_data['nsName'])
        self.assertTrue(ns_found)
        
        self.log('Uninstall namespace (NS1).')
        self.ns.uninstall()

        self.log('Check that namespace (NS1) in namespace list, should not be found.')
        ns_found = self.find_namespace_in_list(zdb, self.ns.default_data['nsName'])
        self.assertFalse(ns_found)