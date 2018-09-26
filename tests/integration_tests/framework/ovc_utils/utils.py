import time
from testconfig import config
from framework.constructor import constructor
from js9 import j
from framework.ovc_utils import *


class OVC_BaseTest(constructor):
    env = config['main']['environment']
    location = config['main']['location']
    repo = 'github.com/openvcloud/0-templates'

    def __init__(self, *args, **kwargs):
        templatespath = ['./framework/ovc_utils/templates', './framework/base_templates']
        super(OVC_BaseTest, self).__init__(templatespath, *args, **kwargs)
        self.ovc_data = {'address': OVC_BaseTest.env,
                         'port': 443,
                         }
        self.ovc_client = self.ovc_client()
        self.CLEANUP = {'users': [], 'accounts': []}

    def setUp(self):
        super(OVC_BaseTest, self).setUp()
        self.key = self.random_string()
        self.openvcloud = self.random_string()
        self.vdcusers = {'gig_qa_1': {'name':'gig_qa_1',
                                      'openvcloud': self.openvcloud,
                                      'provider': 'itsyouonline',
                                      'email': 'dina.magdy.mohammed+123@gmail.com'}}

    def tearDown(self):
        for acc in self.CLEANUP['accounts']:
            if self.check_if_service_exist(acc):
                self.temp_actions = {'account': {'actions': ['uninstall'], 'service': acc}}
                account = {acc: {'openvcloud': self.openvcloud}}
                res = self.create_account(openvcloud=self.openvcloud, vdcusers=self.vdcusers,
                                          accounts=account, temp_actions=self.temp_actions)
                self.wait_for_service_action_status(acc, res[acc]['uninstall'], timeout=20)
        self.delete_services()

    def iyo_jwt(self):
        ito_client = j.clients.itsyouonline.get(instance="main")
        return ito_client.jwt_get(refreshable=True)

    @catch_exception_decoration_return
    def ovc_client(self):
        return j.clients.openvcloud.get(instance='main', data=self.ovc_data)

    def handle_blueprint(self, yaml, **kwargs):
        kwargs['token'] = self.iyo_jwt()
        blueprint = self.create_blueprint(yaml, **kwargs)
        return self.execute_blueprint(blueprint)

    def create_account(self, **kwargs):
        return self.handle_blueprint('account.yaml', **kwargs)

    def create_cs(self, **kwargs):
        return self.handle_blueprint('vdc.yaml', key=self.key, openvcloud=self.openvcloud,
                                     vdcusers=self.vdcusers, **kwargs)

    def create_user(self, **kwargs):
        return self.handle_blueprint('vdcuser.yaml', **kwargs)

    def create_vm(self, **kwargs):
        if 'key' in kwargs.keys():
            return self.handle_blueprint('node.yaml', openvcloud=self.openvcloud,
                                         vdcusers=self.vdcusers, **kwargs)
        return self.handle_blueprint('node.yaml', key=self.key, openvcloud=self.openvcloud,
                                     vdcusers=self.vdcusers, **kwargs)

    def create_disk(self, **kwargs):
        if 'key' in kwargs.keys():
            return self.handle_blueprint('disk.yaml', openvcloud=self.openvcloud,
                                         vdcusers=self.vdcusers, **kwargs)
        return self.handle_blueprint('disk.yaml', key=self.key, openvcloud=self.openvcloud,
                                     vdcusers=self.vdcusers, **kwargs)

    def get_cloudspace(self, name):
        cloudspaces = self.ovc_client.api.cloudapi.cloudspaces.list()
        for cs in cloudspaces:
            if cs['name'] == name:
                return self.ovc_client.api.cloudapi.cloudspaces.get(cloudspaceId=cs['id'])
        return False

    def get_portforward_list(self, cloudspacename, machinename):
        cloudspaceId = self.get_cloudspace(cloudspacename)['id']
        machineId = self.get_vm(cloudspaceId, machinename)['id']
        return self.ovc_client.api.cloudapi.portforwarding.list(cloudspaceId=cloudspaceId, machineId=machineId)

    def get_snapshots_list(self, cloudspacename, machinename):
        cloudspaceId = self.get_cloudspace(cloudspacename)['id']
        machineId = self.get_vm(cloudspaceId, machinename)['id']
        return self.ovc_client.api.cloudapi.machines.listSnapshots(machineId=machineId)

    def get_account(self, name):
        accounts = self.ovc_client.api.cloudapi.accounts.list()
        for account in accounts:
            if account['name'] == name:
                return self.ovc_client.api.cloudapi.accounts.get(accountId=account['id'])
        return False

    def get_vm(self, cloudspaceId, vmname):
        vms = self.ovc_client.api.cloudapi.machines.list(cloudspaceId=cloudspaceId)
        for vm in vms:
            if vm['name'] == vmname:
                return self.ovc_client.api.cloudapi.machines.get(machineId=vm['id'])
        return False

    def get_disks_list(self, account_name):
        accountId = self.get_account(account_name)['id']
        return self.ovc_client.api.cloudapi.disks.list(accountId=accountId)

    def wait_for_cloudspace_status(self, cs, status="DEPLOYED", timeout=100):
        for _ in range(timeout):
            cloudspace = self.get_cloudspace(cs)
            time.sleep(5)
            if cloudspace["status"] == status:
                return True
        return False

    def wait_for_vm_status(self, cs, vm_name, status="RUNNING", timeout=100):
        for _ in range(timeout):
            vm = self.get_vm(cs, vm_name)
            time.sleep(5)
            if vm["status"] == status:
                return True
        return False

    def wait_for_disk(self, cs, vm_name, disk_name, status="exist", timeout=100):
        for _ in range(timeout):
            vm = self.get_vm(cs, vm_name)
            disks = [disk['name'] for disk in vm['disks']]
            time.sleep(5)
            if disk_name in disks:
                if status == "exist":
                    return True
            else:
                if status == "non-exist":
                    return True
        return False
