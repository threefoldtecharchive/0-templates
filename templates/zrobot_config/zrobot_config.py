import os
import signal

from jumpscale import j

from zerorobot.template.base import TemplateBase
from zerorobot.config.data_repo import _parse_zdb
from zerorobot import config

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
        admin_password, hostname, port, namespace = _parse_zdb(self.data['dataRepo'])
        if not port:
            port = 9900
        if not namespace:
            namespace = "default"
        if not admin_password:
            admin_password = ""

        if j.core.state.configGetFromDict("myconfig", "backend") == "db":
            j.tools.configmanager.set_namespace(namespace)
            # Robot should be running using a sandbox
            j.tools.configmanager.configure_keys_from_paths(config.config_repo.key, config.config_repo.key + ".pub")
        else:
            j.core.state.configSetInDict("myconfig", "backend", "db")
            j.core.state.configSetInDict("myconfig", "backend_addr", "{}:{}".format(hostname, port))
            j.core.state.configSetInDict("myconfig", "adminsecret", admin_password)
            j.core.state.configSetInDict("myconfig", "secrets", "")
            j.core.state.configSetInDict("myconfig", "namespace", namespace)

        self._kill_robot()

    def delete(self):
        """
        delete the configuration
        """
        if j.sal.fs.exists(CONFIG_PATH):
            j.sal.fs.remove(CONFIG_PATH)

        # Should reset backend to file
        j.core.state.configSetInDict("myconfig", "backend", "file")
        self._kill_robot()
