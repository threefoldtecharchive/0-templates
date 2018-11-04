from tests.testcases.base_test import BaseTest
import unittest
import time
from random import randint
from zerorobot.dsl.ZeroRobotManager import ServiceCreateError
from tests.controller.controller import Controller

class TestContainer(BaseTest):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setUp(self):
        super().setUp()

    def test001_create_containers(self):
        """ ZRT-ZOS-001
        *Test case for creatings container on a zero-os node*
        **Test Scenario:**
        #. Create a two container on that node, should succeed.
        #. Check that the container have been created.
        """
        self.logger.info('Create a two container on that node, should succeed.')
        container_1_data = self.get_container_default_data()
        self.controller.container_manager.install(wait=True, data=container_1_data)
        self.assertTrue(self.controller.container_manager.install_state, " Installtion state is False")
        self.controller_2 = Controller(config=self.config, god_token=None)        
        container_2_data = self.get_container_default_data()
        self.controller_2.container_manager.install(wait=True, data=container_2_data)
        self.assertTrue(self.controller_2.container_manager.install_state, " Installtion state is False")
    
        self.log('Check that the container have been created.')
        conts = self.controller.node.client.container.list()
        self.assertTrue([c for c in conts.values() if c['container']['arguments']['hostname'] == container_1_data['hostname']])
        self.assertTrue([c for c in conts.values() if c['container']['arguments']['hostname'] == container_2_data['hostname']])

    def test002_create_container_without_flist(self):
        """ ZRT-ZOS-002
        *Test case for creating container without flist*
        **Test Scenario:**
        #. Create a container without providing flist parameter, should fail.
        """
        self.log('Create a container without providing flist parameter, should fail.')
        container_data = self.get_container_default_data()
        container_data["flist"]=""
        with self.assertRaises(ServiceCreateError) as e:
            self.controller.container_manager.install(wait=True, data=container_data)
        self.assertIn("parameter 'flist' not valid: ", e.exception.args[0])

    def test003_create_container_with_env_and_ports_parameters(self):
        """ ZRT-ZOS-003
        *Test case for creating container with env and ports parameter*
        **Test Scenario:**
        #. Create a container with env and ports parameters.
        #. Check if the env and ports parameters have been reflected correctly. 
        """
        self.log('Create a container with env and ports parameters.')
        container_data = self.get_container_default_data()
        env_name = self.random_string()
        env_value = self.random_string()
        destination_port = randint(7000, 8000)      
        container_data["env"] = [{"name":env_name, "value": env_value}]
        container_data["ports"] = ['%s:80'%destination_port]
        self.controller.container_manager.install(wait=True, data=container_data)
        self.assertTrue(self.controller.container_manager.install_state, " Installtion state is False")

        self.log('Check if the parameters have been reflected correctly')
        conts = self.controller.node.client.container.list()
        self.assertTrue([c for c in conts.values() if c['container']['arguments']['hostname'] == container_data['hostname']])
        (cont_id, cont) = [c for c in conts.items() if c[1]['container']['arguments']['hostname'] == container_data['hostname']][0]
        cont_cl = self.controller.node.client.container.client(cont_id)
        self.assertTrue(cont_cl.bash('echo $%s' % env_name).get().stdout.strip(), env_value)
        self.assertTrue(cont['container']['arguments']['port'], {destination_port: 80})

    def test004_start_stop_container(self):
        """ ZRT-ZOS-004
        *Test case for starting and stopping container*
        **Test Scenario:**
        #. Create a container (C1).
        #. Stop container C1, should succeed.
        #. Check if the container has been terminated, should succeed
        #. Start container C1, should succeed.
        #. Check if the container has been started, should succeed
        """
        
        self.logger.info('Create a container (C1)')
        container_data = self.get_container_default_data()
        self.controller.container_manager.install(wait=True, data=container_data)
        self.assertTrue(self.controller.container_manager.install_state, " Installtion state is False")
        self.logger.info('Stop container C1, should succeed.')
        self.controller.container_manager.stop()
        time.sleep(2)
        self.logger.info('Check if the container has been terminated, should succeed')
        conts = self.controller.node.client.container.list()
        self.assertFalse([c for c in conts.values() if c['container']['arguments']['hostname'] == container_data['hostname']])

        self.logger.info('Start container C1, should succeed.')
        self.controller.container_manager.start()
        time.sleep(2)

        self.log('Check if the container has been started, should succeed')
        conts = self.controller.node.client.container.list()
        self.assertTrue([c for c in conts.values() if c['container']['arguments']['hostname'] == container_data['hostname']])

        