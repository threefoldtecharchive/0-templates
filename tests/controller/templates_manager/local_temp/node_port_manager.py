from Jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from testconfig import config
import random
from uuid import uuid4



class NodePortManager:
    def __init__(self, parent):
        self.node_template = 'github.com/threefoldtech/0-templates/node_port_manager/0.0.1'
        self._parent = parent
        self.logger = self._parent.logger
        self.robot = self._parent.remote_robot
        self._node_service = None
        self.guid1 = str(uuid4())
        self.guid2 = str(uuid4())
    @property
    def service(self):
        if self._node_service is None:
            self._node_service = self.robot.services.find(template_name='node_port_manager')[0]
        return self._node_service

    def reserve(self, guid, n):

        return self.service.schedule_action('reserve', {"service_guid": guid, "n": n}).wait(die=True)

    def release(self, guid, ports):

        return self.service.schedule_action('reserve', {"service_guid": guid}, ports).wait(die=True)


