from testconfig import config
from framework.constructor import constructor
from js9 import j
from framework.zos_utils import *
import time
import subprocess


class ZOS_BaseTest(constructor):
    zos_redisaddr = config['main']['redisaddr']
    repo = 'github.com/zero-os/0-templates'


    def __init__(self, *args, **kwargs):
        templatespath = ['./framework/zos_utils/templates', './framework/base_templates']
        super(ZOS_BaseTest, self).__init__(templatespath, *args, **kwargs)

    @classmethod
    def setUpClass(cls):
        cls.zos_client = cls.zos_client(cls, cls.zos_redisaddr)
        cls.cont_flist = 'https://hub.gig.tech/gig-official-apps/ubuntu1604.flist'
        cls.vm_flist = 'https://hub.gig.tech/gig-bootable/ubuntu:16.04.flist'
        cls.cont_storage = 'ardb://hub.gig.tech:16379'
        cls.vm_username = config['main']['username']
        cls.vm_password = config['main']['password']
        cls.zt_token = config['main']['zt_token']
        cls.zt_id = config['main']['zt_id']
        cls.ssh_key= config['main']['sshkey']

    @classmethod
    def tearDownClass(cls):
        cls.delete_services(cls())

    def setUp(self):
        super(ZOS_BaseTest, self).setUp()

    def zos_client(self, ip):
        data = {'host': ip, 'port': 6379,
                'timeout': 100, 'ssl': True}
        return j.clients.zero_os.get(instance='main', data=data)

    def handle_blueprint(self, yaml, **kwargs):
        blueprint = self.create_blueprint(yaml, **kwargs)
        return self.execute_blueprint(blueprint)

    def create_container(self, **kwargs):
        return self.handle_blueprint('container.yaml', **kwargs)

    def create_vm(self, **kwargs):
        return self.handle_blueprint('vm.yaml', **kwargs)

    def check_vnc_connection(self, vnc_ip_port):
        vnc = 'vncdotool -s %s' % vnc_ip_port
        result,error = self.execute_shell_commands(cmd="%s type %s key enter" % (vnc, repr('ls')))
        if 'timeout caused connection failure' in error:
            return False
        return True 
        
    def get_vm(self, vm_name):
        vms = self.zos_client.kvm.list()
        vm = [vm for vm in vms if vm['name'] == vm_name]
        return vm
    
    def execute_command(self, ip, cmd):
        target = "ssh -o 'StrictHostKeyChecking no' root@%s '%s'" % (ip, cmd)
        ssh = subprocess.Popen(target,
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        result = ssh.stdout.readlines()
        error = ssh.stderr.readlines()
        return result, error
