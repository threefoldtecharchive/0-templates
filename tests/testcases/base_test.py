from unittest import TestCase
from testconfig import config
from tests.controller.controller import Controller
from uuid import uuid4
from jumpscale import j
from subprocess import Popen, PIPE, run
import time, os, hashlib

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
        self = cls()
        cls.disks_mount_paths = self.zdb_mounts()
        cls.disk_type = self.select_disk_type()
        cls.mount_paths = self.get_disk_mount_path(cls.disk_type)

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

    def zdb_mounts(self):
        disk_mount=[]
        self.node.zerodbs.prepare()
        storage_pools = self.node.storagepools.list()
        for sp in storage_pools:
            if sp.name == 'zos-cache':
                continue
            try:
                file_system = sp.get('zdb')
            except Exception:
                continue
            disk_name = sp.device[len('/dev/'):-1]
            zdb_mount = file_system.path
            disk_mount.append({'disk': disk_name, 'mountpoint': zdb_mount})
        return disk_mount

    def get_disk_mount_path(self, disk_type):
        disk_RO = '0' if disk_type == "ssd" else '1'
        for disk in self.disks_mount_paths:
            self.disk_name = disk['disk']
            disk_info = self.node.client.disk.getinfo(self.disk_name)
            if disk_info['ro'] == disk_RO:
                disk_path = disk['mountpoint']
                return disk_path

    def get_disks_type(self):
        disks = self.node.client.disk.list()
        disks_type = {'ssd': 0, 'hdd': 0}
        for disk in disks:
            if int(disk["ro"])==0:
                disks_type["ssd"]+=1
            else:
                disks_type["hdd"]+=1
        return disks_type

    def select_disk_type(self):
        disks_info = self.get_disks_type()
        if disks_info['hdd'] > disks_info['ssd']:
            disk_type = 'hdd'
        else:
            disk_type = 'ssd'
            
        return disk_type
