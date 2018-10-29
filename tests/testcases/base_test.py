from unittest import TestCase
from testconfig import config
from tests.controller.controller import Controller
from uuid import uuid4
from jumpscale import j
from subprocess import Popen, PIPE, run
import time, os, hashlib
import itertools

logger = j.logger.get('testsuite.log')

class BaseTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.logger = logger
        self.controller = Controller(config=self.config, god_token=None)
        self.ssh_key = self.load_ssh_key()
        self.node_ip = self.config['robot']['remote_server'][7:-5]
        self.node = self.controller.node
        self.container_flist ="https://hub.grid.tf/tf-bootable/ubuntu:16.04.flist"
        self.container_storage ="zdb://hub.grid.tf:9900"

    @classmethod
    def setUpClass(cls):
        cls.vms = []
        cls.zdbs = []
        cls.vdisks = []
        # self = cls()
        cls.mount_paths = ''

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def execute_cmd(self, cmd):
        sub = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        out, err = sub.communicate()
        return out, err

    def execute_command(self, cmd, ip='', port=22):
        target = "ssh -o 'StrictHostKeyChecking no' -p {} root@{} '{}'".format(port, ip, cmd)
        response = run(target, shell=True, universal_newlines=True, stdout=PIPE, stderr=PIPE)
        # "response" has stderr, stdout and returncode(should be 0 in successful case)
        return response

    def ssh_vm_execute_command(self, vm_ip, cmd, port=22):
        for _ in range(10):            
            resposne = self.execute_command(ip=vm_ip, cmd=cmd, port=port)
            if resposne.returncode:
                time.sleep(25)
            else:
                return resposne.stdout.strip()
        else:
            raise RuntimeError(' [-] {}'.format(resposne.stderr.strip()))

    def calc_md5_checksum(self, file_path):
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _create_directory(self, directory):
        if not os.path.exists(directory):
            os.makedirs(directory)

    def _delete_directory(self, directory):
        os.rmdir(directory)

    def _create_file(self, directory, size):
        with open('/{}/random'.format(directory), 'wb') as fout:
            fout.write(os.urandom(size))  # 1

        file_name = self.calc_md5_checksum('random')

        os.rename('/{}/random'.format(directory), file_name)
        return file_name

    def log(self, msg):
        self.logger.info(msg)

    def check_vnc_connection(self, vnc_ip_port):
        vnc = 'vncdotool -s {} type {} key enter'.format(vnc_ip_port, repr('ls'))
        response = run(vnc, shell=True, universal_newlines=True, stdout=PIPE, stderr=PIPE)
        return response

    def load_ssh_key(self):
        home_user = os.path.expanduser('~')
        if os.path.exists('{}/.ssh/id_rsa.pub'.format(home_user)):
            with open('{}/.ssh/id_rsa.pub'.format(home_user), 'r') as file:
                ssh = file.readline().replace('\n', '')
        else:              
            cmd = 'ssh-keygen -t rsa -N "" -f {}/.ssh/id_rsa -q -P ""; ssh-add {}/.ssh/id_rsa'.format(home_user, home_user)
            run(cmd, shell=True, stdout=PIPE, stderr=PIPE)
            ssh = self.load_ssh_key()
        return ssh

    def random_string(self):
        return str(uuid4()).replace('-', '')[:10]

    def get_zt_ip(self, obj):
        for _ in range(100):
            try:
                ip = obj.info().result['nics'][0]['ip']
                break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError("Can't get zerotier ip")
        return ip

    def generate_combinations(self, data):
        return list(itertools.product(*data))