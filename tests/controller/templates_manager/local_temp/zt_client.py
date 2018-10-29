from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from testconfig import config
import random

class ZT_Client:
    def __init__(self, parent):
        self.zt_template = 'github.com/threefoldtech/0-templates/zerotier_client/0.0.1'
        self._parent = parent
        self.robot = self._parent.remote_robot
        self.service_name = self._parent._generate_random_string()
        self._zt_service = self.robot.services.create(self.zt_template, self.service_name, {'token': config['zt']['zt_client']})

    def uninstall(self):
       return self._zt_service.schedule_action('uninstall')

    def token(self):
       return self._zt_service.schedule_action('token').wait()

    def delete(self):
       return self._zt_service.schedule_action('delete')