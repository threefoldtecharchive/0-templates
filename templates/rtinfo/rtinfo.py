from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError


class Rtinfo(TemplateBase):
    version = "0.0.1"
    template_name = "rtinfo"

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.add_delete_callback(self.uninstall)
        self.recurring_action("_monitor", 600)
        self._node_sal = self.api.node_sal

    def _monitor(self):
        try:
            self.state.check("actions", "install", "ok")
        except StateCheckError:
            return

        addr = "{host}:{port}".format(host=self.data["address"], port=self.data["port"])
        for s in self._node_sal.client.rtinfo.list():
            if s == addr:
                return

        self._node_sal.client.rtinfo.start(self.data["address"], self.data["port"], self.data["disks"])

    def install(self):
        # reinstall if already present
        # stop doesn't throw exception when no service with address/port is present
        self._node_sal.client.rtinfo.stop(self.data["address"], self.data["port"])

        self._node_sal.client.rtinfo.start(self.data["address"], self.data["port"], self.data["disks"])

        self.state.set("actions", "install", "ok")

    def uninstall(self):
        self._node_sal.client.rtinfo.stop(self.data["address"], self.data["port"])
        self.state.delete("actions", "install")
