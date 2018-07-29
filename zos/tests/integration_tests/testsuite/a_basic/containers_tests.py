import unittest
from framework.zos_utils.utils import ZOS_BaseTest
from random import randint


class BasicTests(ZOS_BaseTest):
    def __init__(self, *args, **kwargs):
        super(BasicTests, self).__init__(*args, **kwargs)

    @classmethod
    def setUpClass(cls):
        super(BasicTests, cls).setUpClass()

    def setUp(self):
        super(BasicTests, self).setUp()
        self.temp_actions = {'container': {'actions': ['install']}}

    def test001_create_containers(self):
        """ ZRT-ZOS-001
        *Test case for creatings container on a zero-os node*

        **Test Scenario:**

        #. Create a two container on that node, should succeed.
        #. Check that the container have been created.
        """
        self.log('%s STARTED' % self._testID)

        self.log('Create a two container on that node, should succeed.')
        self.cont1_name = self.random_string()
        self.containers = {self.cont1_name: {'hostname': self.cont1_name,
                                             'flist': self.cont_flist,
                                             'storage': self.cont_storage}}

        self.cont2_name = self.random_string()
        self.containers.update({self.cont2_name: {'hostname': self.cont2_name,
                                                  'flist': self.cont_flist,
                                                  'storage': self.cont_storage}})

        res = self.create_container(containers=self.containers, temp_actions=self.temp_actions)
        self.assertEqual(type(res), type(dict()))
        self.wait_for_service_action_status(self.cont1_name, res[self.cont1_name]['install'])
        self.wait_for_service_action_status(self.cont2_name, res[self.cont2_name]['install'])

        self.log('Check that the container have been created.')
        conts = self.zos_client.container.list()
        self.assertTrue([c for c in conts.values() if c['container']['arguments']['name'] == self.cont1_name])
        self.assertTrue([c for c in conts.values() if c['container']['arguments']['name'] == self.cont2_name])
        cont1 = [c for c in conts.values() if c['container']['arguments']['name'] == self.cont1_name][0]
        self.assertTrue(cont1['container']['arguments']['storage'], self.cont_storage)
        self.assertTrue(cont1['container']['arguments']['root'], self.cont_flist)
        self.assertTrue(cont1['container']['arguments']['hostname'], self.cont_flist)

        self.log('%s ENDED' % self._testID)

    def test002_create_container_with_all_possible_params(self):
        """ ZRT-ZOS-002
        *Test case for creating container with all possible parameters*

        **Test Scenario:**

        #. Create a container without providing flist parameter, should fail.
        #. Create a container with all possible parameters.
        #. Check if the parameters have been reflected correctly.
        """
        self.log('%s STARTED' % self._testID)

        self.log('Create a container without providing flist parameter, should fail.')
        self.cont1_name = self.random_string()
        self.containers = {self.cont1_name: {}}
        res = self.create_container(containers=self.containers, temp_actions=self.temp_actions)
        self.assertEqual(res, "parameter 'flist' not valid: ")

        self.log('Create a container with all possible parameters.')
        self.cont1_name = self.random_string()
        bridge_name = self.random_string()
        env_name = self.random_string()
        env_value = self.random_string()
        self.containers = {self.cont1_name: {'hostname': self.cont1_name,
                                             'flist': self.cont_flist,
                                             'storage': self.cont_storage,
                                             'env': {'name': env_name, 'value': env_value},
                                             'ports': ['8080:80'],
                                             'privileged': True,
                                             'nics': [{'type': 'default'},
                                                      {'type': 'bridge', 'id': bridge_name}],
                                             'hostNetworking': True}}

        res = self.create_container(containers=self.containers, temp_actions=self.temp_actions)
        self.assertEqual(type(res), type(dict()))
        self.wait_for_service_action_status(self.cont1_name, res[self.cont1_name]['install'])

        self.log('Check if the parameters have been reflected correctly')
        conts = self.zos_client.container.list()
        self.assertTrue([c for c in conts.values() if c['container']['arguments']['name'] == self.cont1_name])

        (cont1_id, cont1) = [c for c in conts.items() if c[1]['container']['arguments']['name'] == self.cont1_name][0]
        cont1_cl = self.zos_client.container.client(cont1_id)
        self.assertTrue(cont1_cl.bash('echo $%s' % env_name).get().stdout.strip(), env_value)
        self.assertTrue(cont1['container']['arguments']['host_network'], True)
        self.assertTrue(cont1['container']['arguments']['port'], {'8080': 80})

        nics = cont1['container']['arguments']['nics']
        nic = [nic for nic in nics if nic['type'] == 'bridge'][0]
        self.assertTrue(len(nics), 2)
        self.assertEqual(nic['id'], bridge_name)

        self.log('%s ENDED' % self._testID)

    def test003_start_stop_container(self):
        """ ZRT-ZOS-003
        *Test case for starting and stopping container*

        **Test Scenario:**

        #. Create a container (C1).
        #. Start container C1, should succeed.
        #. Check if the container has been terminated, should succeed
        #. Stop container C1, should succeed.
        #. Check if the container has been started, should succeed
        """

        self.log('%s STARTED' % self._testID)

        self.log('Create a container (C1)')
        self.cont1_name = self.random_string()
        self.containers = {self.cont1_name: {'hostname': self.cont1_name,
                                             'flist': self.cont_flist,
                                             'storage': self.cont_storage}}

        res = self.create_container(containers=self.containers, temp_actions=self.temp_actions)
        self.assertEqual(type(res), type(dict()))
        self.wait_for_service_action_status(self.cont1_name, res[self.cont1_name]['install'])

        self.log('Stop container C1, should succeed.')
        temp_actions = {'container': {'actions': ['stop'], 'service': self.cont1_name}}
        res = self.create_container(containers=self.containers, temp_actions=temp_actions)
        self.wait_for_service_action_status(self.cont1_name, res[self.cont1_name]['stop'])

        self.log('Check if the container has been terminated, should succeed')
        conts = self.zos_client.container.list()
        self.assertFalse([c for c in conts.values() if c['container']['arguments']['name'] == self.cont1_name])

        self.log('Start container C1, should succeed.')
        temp_actions = {'container': {'actions': ['start'], 'service': self.cont1_name}}
        res = self.create_container(containers=self.containers, temp_actions=temp_actions)
        self.wait_for_service_action_status(self.cont1_name, res[self.cont1_name]['start'])

        self.log('Check if the container has been started, should succeed')
        conts = self.zos_client.container.list()
        self.assertTrue([c for c in conts.values() if c['container']['arguments']['name'] == self.cont1_name])

        self.log('%s ENDED' % self._testID)
