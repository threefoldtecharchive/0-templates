from tests.testcases.base_test import BaseTest
from nose_parameterized import parameterized
import unittest
import time, requests
from random import randint
from zerorobot.dsl.ZeroRobotManager import ServiceCreateError
from tests.controller.controller import Controller

class TestContainer(BaseTest):
    def setUp(self):
        super().setUp()
        self.containers = []

    def tearDown(self):
        for container in self.containers:
            container.uninstall()
        self.containers.clear()
        super().tearDown()

    def test001_create_container_without_flist(self):
        """ ZRT-ZOS-001
        *Test case for creating container without flist*
        **Test Scenario:**
        #. Create a container without providing flist parameter, should fail.
        """
        self.log('Create a container without providing flist parameter, should fail.')
        container = self.controller.container_manager(parent=self.controller, service_name=None)
        with self.assertRaises(ServiceCreateError) as e:
            container.install(wait=True, flist="")
        self.assertIn("parameter 'flist' not valid: ", e.exception.args[0])

    def test002_create_container_with_env_parameter(self):
        """ ZRT-ZOS-002
        *Test case for creating container with env parameter*
        **Test Scenario:**
        #. Create a container with env  parameter.
        #. Check if the env parameter have been reflected correctly. 
        """
        self.log('Create a container with env parameters.')
        env_name = self.random_string()
        env_value = self.random_string()
        container = self.controller.container_manager(parent=self.controller, service_name=None)
        container.install(wait=True, env=[{"name":env_name, "value": env_value}])
        self.containers.append(container)
        self.assertTrue(container.install_state, " Installtion state is False")

        self.log('Check if the parameter have been reflected correctly')
        conts = self.node.client.container.list()
        self.assertTrue([c for c in conts.values() if c['container']['arguments']['hostname'] == container.data['hostname']])
        (cont_id, cont) = [c for c in conts.items() if c[1]['container']['arguments']['hostname'] == container.data['hostname']][0]
        cont_cl = self.node.client.container.client(cont_id)
        self.assertTrue(cont_cl.bash('echo $%s' % env_name).get().stdout.strip(), env_value)

    def test003_start_stop_container(self):
        """ ZRT-ZOS-003
        *Test case for starting and stopping container*
        **Test Scenario:**
        #. Create a container (C1).
        #. Stop container C1, should succeed.
        #. Check if the container has been terminated, should succeed
        #. Start container C1, should succeed.
        #. Check if the container has been started, should succeed
        """
        self.logger.info('Create a container (C1)')
        container = self.controller.container_manager(parent=self.controller, service_name=None)
        container.install(wait=True)
        self.containers.append(container)
        self.assertTrue(container.install_state, " Installtion state is False")

        self.logger.info('Stop container C1, should succeed.')
        container.stop()
        time.sleep(2)
        self.logger.info('Check if the container has been terminated, should succeed')
        conts = self.node.client.container.list()
        self.assertFalse([c for c in conts.values() if c['container']['arguments']['hostname'] == container.data['hostname']])

        self.logger.info('Start container C1, should succeed.')
        container.start()
        time.sleep(2)

        self.log('Check if the container has been started, should succeed')
        conts = self.node.client.container.list()
        self.assertTrue([c for c in conts.values() if c['container']['arguments']['hostname'] == container.data['hostname']])

    @parameterized.expand(['before', 'after'])
    @unittest.skip('https://github.com/threefoldtech/0-templates/issues/201')
    def test004_create_container_with_zt_nic(self, add):
        """ ZRT-ZOS-016
        *Test case for creating container with zerotier network*
        **Test Scenario:**

        #. Create a container (C1).
        #. Add zerotier network to container (c1).
        #. Check that netwrok is added successfully to the container.
        """
        self.logger.info('Create a container (C1)')
        zt_network = [{'name': self.random_string(), 'type': 'zerotier', 'id': self.zt_id}, {'type': 'default', 'name': 'defaultnic'}]
        container = self.controller.container_manager(parent=self.controller, service_name=None)
        if add == 'before':
            zt_network[0]['token'] = self.config['zt']['zt_client']
            container.install(wait=True, nics=zt_network)
        else:
            container.install(wait=True)
            container.add_nic(zt_network[0])
        self.containers.append(container)
        self.assertTrue(container.install_state, " Installtion state is False")

        self.log('Check that netwrok is added successfully to the container.')
        conts = self.node.containers.list()
        cont = [c for c in conts if container.data['hostname'] in c.hostname][0]
        self.assertEqual(cont.nics[0]['type'], 'zerotier')

    def test005_add_mount_container(self):
        """ ZRT-ZOS-017
        *Test case for adding mount directory to container*
        **Test Scenario:**

        #. Create a directory (D1) on host and file (F1) inside it.
        #. Create a container (C1) with mount directory (D1), should succeed.
        #. Get container id and container client.
        #. Check that file (F1) is in target mount directory, should be found.
        """
        self.log('Create a directory (D1) on host and file (F1) inside it.')
        dir_path = '/{}'.format(self.random_string())
        file_name = self.random_string()
        data = self.random_string()
        self.node.client.filesystem.mkdir(dir_path)
        self.node.client.bash('echo {} > {}/{}'.format(data, dir_path, file_name))
        
        self.logger.info('Create a container (C1) with mount directory (D1), should succeed.')
        container = self.controller.container_manager(parent=self.controller, service_name=None)
        container.install(wait=True, mounts=[{'source': dir_path, 'target': '/mnt'}])
        self.containers.append(container)
        self.assertTrue(container.install_state, " Installtion state is False")

        self.log('Get container id and container client.')
        conts = self.node.containers.list()
        cont = [c for c in conts if container.data['hostname'] in c.hostname][0]
        client = self.node.client.container.client(cont.id)

        self.log('Check that file (F1) is in target mount directory, should be found.')
        content = client.bash('cat /mnt/{}'.format(file_name)).get().stdout.strip()
        self.assertEqual(content, data)

        self.log('Remove directory created')
        self.node.client.bash('rm -rf {}'.format(dir_path))
        
    def test006_add_port_forward_to_container(self):
        """ ZRT-ZOS-018
        *Test case for adding port forward to container*
        **Test Scenario:**
        #. Create a container (C1) with port forward (P1).
        #. Get container id and client.
        #. Create server on port (P1).
        #. Create a file (F1) on container (C1).
        #. Try to get file (F1) through server using port forward, should be found. 
        """
        self.log('Create a container with port forward')
        host_port = randint(7000, 8000)
        guest_port = randint(3000, 4000)
        container = self.controller.container_manager(parent=self.controller, service_name=None)
        container.install(wait=True, ports=['{}:{}'.format(host_port, guest_port)])
        self.containers.append(container)
        self.assertTrue(container.install_state, " Installtion state is False")

        self.log('Get container id and client.')
        conts = self.node.containers.list()
        cont = [c for c in conts if container.data['hostname'] in c.hostname][0]
        client = self.node.client.container.client(cont.id)
        
        self.log('Create server on port (P1).')
        client.bash('python3 -m http.server {} &> /tmp/server.log &'.format(guest_port))
        time.sleep(10)

        self.log('Create a file (F1) on container (C1).')
        dir_path = '/{}'.format(self.random_string())
        file_path = '{}/{}'.format(dir_path, self.random_string())
        data = self.random_string()
        client.filesystem.mkdir(dir_path)
        client.bash('echo {} > {}'.format(data, file_path))

        self.log('Try to get file (F1) through server using port forward, should be found. ')
        response = requests.get('http://{}:{}{}'.format(self.node_ip, host_port, file_path))
        content = response.content.decode('utf-8').strip()
        self.assertEqual(content, data)
    
    @unittest.skip('https://github.com/threefoldtech/0-templates/issues/205')
    def test007_add_initprocess_to_container(self):
        """ ZRT-ZOS-019
        *Test case for adding init process to container*
        **Test Scenario:**
        #. Create a container (C1) with init process.
        #. Get container id and client.
        #. Check that process is created, should be found. 
        """
        self.log('Create a container (C1) with init process.')
        container = self.controller.container_manager(parent=self.controller, service_name=None)
        pid = str(randint(500, 1000))
        container.install(wait=True, initProcesses=[{'name': 'sleep', 'args': ['1000s'], 'id': pid}])
        self.containers.append(container)
        self.assertTrue(container.install_state, " Installtion state is False")

        self.log('Get container id and client.')
        conts = self.node.containers.list()
        cont = [c for c in conts if container.data['hostname'] in c.hostname][0]
        client = self.node.client.container.client(cont.id)
        
        self.log('Check that process is created, should be found.')
        processes = client.process.list()
        process = [p for p in processes if p['name'] == 'sleep'][0]
        self.assertEqual(process['pid'], '3777')
        self.assertEqual(process['cmdline'], '/bin/sleep 1000s')
    
    def test008_create_containers_with_same_port_forward(self):
        """ ZRT-ZOS-020
        *Test case for creating container with same port forward*
        **Test Scenario:**
        #. Create a container (C1) with port forward (P1).
        #. Create another container (C2) with same port forward (P1), should fail.
        #. Stop container (C1).
        #. Create another container (C3) with same port forward (P1), should success.
        """
        self.log('Create a container (C1) with port forward (P1).')
        host_port = randint(7000, 8000)
        guest_port = randint(3000, 4000)
        container = self.controller.container_manager(parent=self.controller, service_name=None)
        container.install(wait=True, ports=['{}:{}'.format(host_port, guest_port)])
        self.assertTrue(container.install_state, " Installtion state is False")

        self.log('Create another container (C2) with same port forward (P1), should fail.')
        with self.assertRaises(RuntimeError) as e:
            container1 = self.controller.container_manager(parent=self.controller, service_name=None)
            container1.install(wait=True, ports=['{}:{}'.format(host_port, guest_port)])

        self.log('Stop container (C1).')
        container.stop()

        self.log('Create another container (C3) with same port forward (P1), should success.')
        container2 = self.controller.container_manager(parent=self.controller, service_name=None)
        container2.install(wait=True, ports=['{}:{}'.format(host_port, guest_port)])
        self.containers.append(container2)
        self.assertTrue(container.install_state, " Installtion state is False")

    @parameterized.expand(['False', 'True'])
    def test009_create_containers_with_host_network(self, host_network):
        """ ZRT-ZOS-020
        *Test case for creating container with host network parameter*
        **Test Scenario:**
        #. Create a container (C1) with host network parameter.
        #. Get container id and client.
        #. Try to reach the network.
   
        """
        self.log('Create a container (C1) without nics.')
        container = self.controller.container_manager(parent=self.controller, service_name=None)
        if host_network == 'True':
            container.install(wait=True, nics=[], hostNetworking=True)
        else:
            container.install(wait=True, nics=[], hostNetworking=False)
        self.containers.append(container)
        self.assertTrue(container.install_state, " Installtion state is False")

        self.log('Get container id and client.')
        conts = self.node.containers.list()
        cont = [c for c in conts if container.data['hostname'] in c.hostname][0]
        client = self.node.client.container.client(cont.id)

        self.log('Try to reach the network, should fail.')
        result = client.bash('ping 8.8.8.8 -w 5').get()
        if host_network == 'True':
            self.assertFalse(result.code)
            self.assertEqual(result.state, 'SUCCESS')
        else:
            self.assertTrue(result.code)
            self.assertEqual(result.state, 'ERROR')
            self.assertEqual(result.stderr.strip(), 'connect: Network is unreachable')
