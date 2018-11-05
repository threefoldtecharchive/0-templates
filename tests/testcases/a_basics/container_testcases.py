from tests.testcases.base_test import BaseTest
import unittest
import time
from random import randint
from zerorobot.dsl.ZeroRobotManager import ServiceCreateError
from tests.controller.controller import Controller

class TestContainer(BaseTest):
    def test001_create_container_without_flist(self):
        """ ZRT-ZOS-001
        *Test case for creating container without flist*
        **Test Scenario:**
        #. Create a container without providing flist parameter, should fail.
        """
        self.log('Create a container without providing flist parameter, should fail.')
        with self.assertRaises(ServiceCreateError) as e:
            self.controller.container_manager.install(wait=True, flist="")
        self.assertIn("parameter 'flist' not valid: ", e.exception.args[0])

    def test002_create_container_with_env_and_ports_parameters(self):
        """ ZRT-ZOS-002
        *Test case for creating container with env and ports parameter*
        **Test Scenario:**
        #. Create a container with env and ports parameters.
        #. Check if the env and ports parameters have been reflected correctly. 
        """
        self.log('Create a container with env and ports parameters.')
        env_name = self.random_string()
        env_value = self.random_string()
        destination_port = randint(7000, 8000)      
        self.controller.container_manager.install(wait=True, env=[{"name":env_name, "value": env_value}], ports=['%s:80'%destination_port])
        self.assertTrue(self.controller.container_manager.install_state, " Installtion state is False")

        self.log('Check if the parameters have been reflected correctly')
        conts = self.controller.node.client.container.list()
        self.assertTrue([c for c in conts.values() if c['container']['arguments']['hostname'] == self.controller.container_manager.data['hostname']])
        (cont_id, cont) = [c for c in conts.items() if c[1]['container']['arguments']['hostname'] == self.controller.container_manager.data['hostname']][0]
        cont_cl = self.controller.node.client.container.client(cont_id)
        self.assertTrue(cont_cl.bash('echo $%s' % env_name).get().stdout.strip(), env_value)
        self.assertTrue(cont['container']['arguments']['port'], {destination_port: 80})

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
        self.controller.container_manager.install(wait=True)
        self.assertTrue(self.controller.container_manager.install_state, " Installtion state is False")
        self.logger.info('Stop container C1, should succeed.')
        self.controller.container_manager.stop()
        time.sleep(2)
        self.logger.info('Check if the container has been terminated, should succeed')
        conts = self.controller.node.client.container.list()
        self.assertFalse([c for c in conts.values() if c['container']['arguments']['hostname'] == self.controller.container_manager.data['hostname']])

        self.logger.info('Start container C1, should succeed.')
        self.controller.container_manager.start()
        time.sleep(2)

        self.log('Check if the container has been started, should succeed')
        conts = self.controller.node.client.container.list()
        self.assertTrue([c for c in conts.values() if c['container']['arguments']['hostname'] == self.controller.container_manager.data['hostname']])

        