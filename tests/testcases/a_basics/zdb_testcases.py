from tests.testcases.base_test import BaseTest
from nose_parameterized import parameterized
import unittest
import time, random


class BasicTests(BaseTest):
    def setUp(self):
        super().setUp()

    def test001_get_list_zerodb_info(self):
            """ ZRT-ZOS-009
            *Test case for listing and getting zerodb information*

            **Test Scenario:**

            #. Create zerodb (zdb) with basic params, should succeed.
            #. Check that the params has been reflected correctly.
            #. List the namespaces, should be empty.
            #. Create namespace (NS), should succeed.
            #. List namespaces, NS should be found.
            #. Set the namespace (Ns) settings.
            #. Check that NS setting has been changed.
            """
            self.log('Create zerodb (zdb) with basic params, should succeed')
            data={'name': self.random_string(),
                    'sync': True,
                    'mode': 'user',
                    'admin': self.random_string(),
                    'path': '/var/cache'}
            zdb = self.controller.zdb_manager
            zdb.install(data, wait=True)

            import ipdb; ipdb.set_trace()

            self.log('Check that the params has been reflected correctly.')
            container = self.node.client.container.find('zerodb_' + data['name'])
            zdb_cl = self.node.client.container.client(list(container.keys())[0])
            jobs = zdb_cl.job.list()
            job_id = 'zerodb.' + data['name']
            job_args = [job for job in jobs if job['cmd']['id'] == job_id][0]['cmd']['arguments']['args']
            self.assertIn('user', job_args)
            self.assertIn('--sync', job_args)
            self.assertIn(data['admin'], job_args)

            self.log('list the namespaces, should be empty')
            namespaces = zdb.namespace_list()
            self.assertEqual(namespaces.result, [])

            self.log('Create namespace (NS), should succeed')
            ns_name = self.random_string()
            namespace = zdb.namespace_create(data={'name': ns_name})
            time.sleep(2)
            self.assertEqual(namespace.state, 'ok')

            self.log('List namespaces, NS should be found')
            namespaces = zdb.namespace_list()
            self.assertEqual(len(namespaces.result), 1)
            self.assertEqual(namespaces.result[0]['name'], ns_name)

            self.log('set the namespace (NS) settings')
            size = random.randint(1, 9)
            zdb.namespace_set(data={'name': ns_name, 'value': self.random_string(), 'prop': 'password'})
            zdb.namespace_set(data={'name': ns_name, 'value': False, 'prop': 'public'})
            zdb.namespace_set(data={'name': ns_name, 'value': size, 'prop': 'size'})

            self.log('Check that NS setting has been changed')
            ns_info = zdb.namespace_info(ns_name).wait()
            self.assertEqual(ns_info.result['public'], 'no')
            self.assertEqual(ns_info.result['password'], 'yes')
            namespaces = zdb.namespace_list()
            self.assertEqual(namespaces.result[0]['size'], size)
            zdb.stop().wait(die=True, timeout=30)

    def test002_start_stop_zerodb(self):
            """ ZRT-ZOS-010
            *Test case for starting and stopping zerodb service*

            **Test Scenario:**

            #. Create zerodb (zdb).
            #. Create namespace (NS), should succeed.
            #. Stop zerodb service, should succeed.
            #. Make sure zerodb container has been removed.
            #. Start zerodb service, should succeed.
            #. Check that Namespace (NS) is still there.
            """
            data={'name': self.random_string(),
                    'sync': True,
                    'mode': 'user',
                    'admin': self.random_string(),
                    'path': '/mnt/storagepools/b8b1dadd-cf94-44d3-a4dc-5aab7232eb98/filesystems/zdb'}
            zdb = self.controller.zdb_manager
            zdb.install(data, wait=True)

            self.log('Create namespace (NS), should succeed')
            ns_name = self.random_string()
            namespace = zdb.namespace_create(data={'name': ns_name})
            time.sleep(2)
            self.assertEqual(namespace.state, 'ok')

            self.log('Stop zerodb service, should succeed')
            zdb.stop().wait(die=True, timeout=30)

            self.log('Make sure zerodb container has been removed')
            conts = self.node.client.container.list()
            self.assertFalse([c for c in conts.values() if data['name'] in c['container']['arguments']['name']])

            self.log('Start zerodb service, should succeed.')
            zdb.start().wait(die=True, timeout=30)
            conts = self.node.client.container.list()
            self.assertTrue([c for c in conts.values() if data['name'] in c['container']['arguments']['name']])

            self.log('Check that Namespace (NS) is still there.')
            namespaces = zdb.namespace_list()
            self.assertEqual(len(namespaces.result), 1)
            self.assertEqual(namespaces.result[0]['name'], ns_name)
            zdb.stop()

