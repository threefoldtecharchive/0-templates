import os
import signal

from jumpscale import j

from zerorobot.template.base import TemplateBase
from zerorobot.config.data_repo import _parse_zdb

CONFIG_PATH = '/opt/var/data/zrobot/zrobot_data/data_repo.yaml'


class ZrobotConfig(TemplateBase):

    version = '0.0.1'
    template_name = "zrobot_config"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)

    def validate(self):
        _parse_zdb(self.data['dataRepo'])

    def _kill_robot(self):
        os.kill(os.getpid(), signal.SIGTERM)

    def install(self):
        """
        install writes the config, then send a signal to the robot to stop itself
        in production 0-os will detect that the robot stops and will restart it
        """

        j.data.serializer.yaml.dump(
            CONFIG_PATH,
            {'zdb_url': self.data['dataRepo']}
        )
        self._kill_robot()

    def delete(self):
        """
        delete the configuration
        """
        if j.sal.fs.exists(CONFIG_PATH):
            j.sal.fs.remove(CONFIG_PATH)

        self._kill_robot()
