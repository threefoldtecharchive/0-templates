from jumpscale import j
from zerorobot.task import TASK_STATE_OK
from zerorobot.template.base import TemplateBase

NODE_CLIENT = 'local'


class Upgrader(TemplateBase):

    version = '0.0.1'
    template_name = "upgrader"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self._node_sal = j.clients.zos.get(NODE_CLIENT)

    def upgrade_robot(self):
        self.state.set('robot_upgrade', 'running', 'ok')
        # just stop the robot container, it will be respawned automatically
        zcont = self._node_sal.containers.get('zrobot')
        zcont.stop()
        self.state.delete('robot_upgrade', 'running')

    def upgrade_zdb(self):
        self.state.set('zdb_upgrade', 'running', 'ok')
        for zdb in self.api.services.find(template_name='zerodb'):
            task = zdb.schedule_action('upgrade')
            task.wait()
            if task.state != TASK_STATE_OK:
                self.logger.error('error upgrading zerodb %s: %s', task.service.name)
            else:
                self.logger.info('zerodb %s upgraded', task.service.name)
        self.state.delete('zdb_upgrade', 'running')

    def reboot_host(self):
        self.logger.info("rebooting")
        self._node_sal.reboot()
