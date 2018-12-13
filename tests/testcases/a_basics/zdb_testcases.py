from tests.testcases.base_test import BaseTest
from nose_parameterized import parameterized
import unittest
import time, random

class ZDBTestCases(BaseTest):  

    def tearDown(self):
        for zdb in self.zdbs:
            namespaces = zdb.namespace_list().result
            for namespace in namespaces:
                zdb.namespace_delete(namespace['name'])
            zdb.stop()
            zdb.service.delete()
        self.zdbs.clear()
        super().tearDown()

    @parameterized.expand(['user', 'seq', 'direct'])
    @unittest.skip('https://github.com/threefoldtech/jumpscale_lib/issues/208')
    def test001_create_zdb(self, mode):
        """ ZRT-ZOS-018
        *Test case for creating zerodb *

        **Test Scenario:**

        #. Create zerodb (zdb) with basic params, should succeed.
        #. Check that the params has been reflected correctly.
        """
        self.log('Create zerodb (zdb) with basic params, should succeed')
        admin_passwd = self.random_string()
        zdb = self.controller.zdb_manager
        zdb.install(wait=True, path=self.mount_paths, admin=admin_passwd, mode=mode)

        self.log('Check that the params has been reflected correctly.')
        container_name = 'zerodb_' + zdb.zdb_service_name
        container = self.node.client.container.find(container_name)
        zdb_cl = self.node.client.container.client(list(container.keys())[0])
        jobs = zdb_cl.job.list()
        job_id = 'zerodb.' + zdb.zdb_service_name
        job_args = [job for job in jobs if job['cmd']['id'] == job_id][0]['cmd']['arguments']['args']
        self.assertIn('user', job_args)
        self.assertIn('--sync', job_args)
        self.assertIn(admin_passwd, job_args)
        self.zdbs.append(zdb)
        
    def test002_create_list_namespaces(self):
        """ ZRT-ZOS-019
        *Test case for creating and listing namespaces*

        **Test Scenario:**

        #. Create zerodb (zdb) with basic params, should succeed.
        #. List the namespaces, should be empty.
        #. Create namespace (NS), should succeed.
        #. List namespaces, NS should be found.
        """
        self.log('Create zerodb (zdb) with basic params, should succeed')
        admin_passwd = self.random_string()
        zdb = self.controller.zdb_manager
        zdb.install(wait=True, path=self.mount_paths, admin=admin_passwd)

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
        self.zdbs.append(zdb)

    @parameterized.expand(['password', 'public', 'size'])
    def test003_set_namespace_properities(self, prop):
        """ ZRT-ZOS-020
        *Test case for setting namespace properities*

        **Test Scenario:**

        #. Create zerodb (zdb) with basic params, should succeed.
        #. Create namespace (NS), should succeed.
        #. set the namespace (NS) properities.
        #. Check that NS properities has been changed.
        """
        self.log('Create zerodb (zdb) with basic params, should succeed')
        admin_passwd = self.random_string()
        zdb = self.controller.zdb_manager
        zdb.install(wait=True, path=self.mount_paths, admin=admin_passwd)

        self.log('Create namespace (NS), should succeed')
        ns_name = self.random_string()
        namespace = zdb.namespace_create(data={'name': ns_name})
        time.sleep(2)
        self.assertEqual(namespace.state, 'ok')

        if prop == 'password':
            value = self.random_string()
            check_value = 'yes'
        elif prop == 'public':
            value = False
            check_value = 'no'
        else:
            value = random.randint(1, 9)

        self.log('set the namespace (NS) settings')
        zdb.namespace_set(data={'name': ns_name, 'value': value, 'prop': prop})

        self.log('Check that NS setting has been changed')
        if prop in ['public', 'password']:
            ns_info = zdb.namespace_info(ns_name).wait()
            self.assertEqual(ns_info.result[prop], check_value)
        else:
            namespaces = zdb.namespace_list()
            self.assertEqual(namespaces.result[0][prop], value)
        self.zdbs.append(zdb)

    def test004_start_stop_zerodb(self):
        """ ZRT-ZOS-021
        *Test case for starting and stopping zerodb service*

        **Test Scenario:**

        #. Create zerodb (zdb).
        #. Create namespace (NS), should succeed.
        #. Stop zerodb service, should succeed.
        #. Make sure zerodb container has been removed.
        #. Start zerodb service, should succeed.
        #. Check that Namespace (NS) is still there.
        """
        zdb = self.controller.zdb_manager
        zdb.install(wait=True, path=self.mount_paths)

        self.log('Create namespace (NS), should succeed')
        ns_name = self.random_string()
        namespace = zdb.namespace_create(data={'name': ns_name})
        time.sleep(2)
        self.assertEqual(namespace.state, 'ok')

        self.log('Stop zerodb service, should succeed')
        zdb.stop().wait(die=True, timeout=30)

        self.log('Make sure zerodb container has been removed')
        conts = self.node.client.container.list()
        self.assertFalse([c for c in conts.values() if zdb.zdb_service_name in c['container']['arguments']['name']])

        self.log('Start zerodb service, should succeed.')
        zdb.start().wait(die=True, timeout=30)
        conts = self.node.client.container.list()
        self.assertTrue([c for c in conts.values() if zdb.zdb_service_name in c['container']['arguments']['name']])

        self.log('Check that Namespace (NS) is still there.')
        namespaces = zdb.namespace_list()
        self.assertEqual(len(namespaces.result), 1)
        self.assertEqual(namespaces.result[0]['name'], ns_name)
        self.zdbs.append(zdb)

    def test005_delete_namespaces(self):
        """ ZRT-ZOS-022
        *Test case for deleting namespaces*

        **Test Scenario:**

        #. Create zerodb (zdb) with namespace, should succeed.
        #. List namespaces, NS should be found.
        #. Delete namespace (NS), should succeed. 
        #. List namesapces, should be empty. 
        """
        self.log('Create zerodb (zdb) with basic params, should succeed')
        ns_name = self.random_string()
        namespace = [{'name': ns_name, 'size': random.randint(1, 30), 'password': self.random_string(), 'public': False}]
        zdb = self.controller.zdb_manager
        zdb.install(wait=True, path=self.mount_paths, namespaces=namespace)
        self.zdbs.append(zdb)

        self.log('List namespaces, NS should be found')
        namespaces = zdb.namespace_list()
        self.assertEqual(len(namespaces.result), 1)
        self.assertEqual(namespaces.result[0]['name'], ns_name)
        response = self.node.client.bash("ls {}/data/{}".format(self.mount_paths, ns_name)).get()
        self.assertEqual(response.state, 'SUCCESS')

        self.log("Delete namespace (NS), should succeed.")
        delete = zdb.namespace_delete(name=ns_name)
        time.sleep(2)
        self.assertEqual(delete.state, 'ok')

        self.log('list the namespaces, should be empty')
        namespaces = zdb.namespace_list()
        self.assertEqual(namespaces.result, [])
        response = self.node.client.bash("ls {}/data/{}".format(self.mount_paths, ns_name)).get()
        self.assertEqual(response.state, 'ERROR')
        self.assertIn("No such file or directory", response.stderr.strip())
    
    def test006_zdb_with_zerotier_nics(self):
        """ ZRT-ZOS-023
        *Test case for creating zdb with zerotier network*

        **Test Scenario:**

        #. Create zerodb (zdb) with zerotier network, should succeed.
        #. Check that zdb got a zerotier ip.
        """
        self.log('Create zerodb (zdb) with basic params, should succeed')
        zt_client = self.controller.zt_client(self.controller)
        zt_network = [{'name': self.random_string(), 'type': 'zerotier', 'id': self.zt_id, 'ztClient': zt_client.service_name}]
        zdb = self.controller.zdb_manager
        zdb.install(wait=True, path=self.mount_paths, nics=zt_network)
        self.zdbs.append(zdb)

        self.log("Check that zdb got a zerotier ip.")
        name = 'zerodb_' + zdb.default_data['name']
        cont = self.node.containers.get(name)
        ip = self.get_zerotier_ip(cont.identity)
        self.assertTrue(ip)