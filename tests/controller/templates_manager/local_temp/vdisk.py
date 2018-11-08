from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from testconfig import config
import random

class VdiskManager:
    def __init__(self, parent, service_name=None):
        self.vdisk_template = 'github.com/threefoldtech/0-templates/vdisk/0.0.1'
        self._parent = parent
        self.logger = self._parent.logger
        self.robot = self._parent.remote_robot
        self._vdisk_service = service_name
        if service_name:
            self._vdisk_service = self.robot.service.get(name=service_name)

    @property
    def service(self):
        if self._vdisk_service == None:
            self.logger.error('- Vdisk_service is None, Install it first.')
        else:
            return self._vdisk_service

    def install(self, wait=True, **kwargs):
        filesystem=['ext4', 'ext3', 'ext2', 'btrfs']
        default_data = {
            'nsName': self._parent._generate_random_string(),
            'zerodb': '',
            'diskType': 'ssd',
            'size': random.randint(1, 20),
            'mountPoint': '/mnt/{}'.format(self._parent._generate_random_string()),
            'filesystem': random.choice(filesystem),
            'label': self._parent._generate_random_string(),
        }
        if kwargs:
            default_data.update(kwargs)

        self.vdisk_service_name = default_data['nsName']
        self._vdisk_service = self.robot.services.create(self.vdisk_template, self.vdisk_service_name, default_data)
        self._vdisk_service.schedule_action('install').wait(die=wait)

    def uninstall(self, wait=True):
        self.service.schedule_action('uninstall').wait(die=wait)

    def info(self):
        return self.service.schedule_action('info').wait()

    def url(self):
        return self.service.schedule_action('url')
    
    def private_url(self):
        return self.service.schedule_action('private_url')