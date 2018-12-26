from Jumpscale import j
from uuid import uuid4
from testconfig import config
from tests.controller.templates_manager.local_temp import vm, container, zerodb, vdisk, gateway, namespace, bridge, node , node_port_manager
from tests.controller.templates_manager.general_temp import zt_client, dm_vm

logger = j.logger.get('controller.log')
node_remote = j.clients.zos.get('remote_node', data={'host': config['robot']['remote_server'][7:-5]})
zcont = node_remote.containers.get('zrobot')
resp = zcont.client.system('zrobot godtoken get').get()
god_token = resp.stdout.split(':', 1)[1].strip()


class Controller:
    def __init__(self, config):
        self.logger = logger
        self.config = config
        # local robot
        j.clients.zrobot.get(self.config['robot']['client'], data={'url': config['robot']['server']})
        self.robot = j.clients.zrobot.robots[self.config['robot']['client']]

        # remote robot
        j.clients.zrobot.get(self.config['robot']['remote_client'],
                             data={'url': config['robot']['remote_server'],
                             'god_token_': god_token})
        self.remote_robot = j.clients.zrobot.robots[self.config['robot']['remote_client']]
        self.node = node_remote

        # get instance from all templates_manager
        self.vm_manager = vm.VMManager(parent=self, service_name=None)
        self.node_port_manager = node_port_manager.NodePortManager(parent=self)
        self.dm_vm = dm_vm.DMVMManager(parent=self, service_name=None)
        self.zdb_manager = zerodb.ZDBManager(parent=self, service_name=None)
        self.vdisk = vdisk.VdiskManager(parent=self, service_name=None)
        self.ns_manager = namespace.NSManager(parent=self, service_name=None)
        self.node_manager = node.NodeManager(parent=self)
        self.bridge_manager = bridge.BrigeManager(parent=self, service_name=None)
        self.container_manager = container.ContManager
        self.zt_client = zt_client.ZT_Client
        self.gw_manager = gateway.GWManager

    def random_string(self):
        return str(uuid4()).replace('-', '')[10:]
