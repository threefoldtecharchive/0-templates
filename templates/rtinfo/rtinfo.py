from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError

NODE_CLIENT = "local"


class Rtinfo(TemplateBase):
    version = "0.0.1"
    template_name = "rtinfo"

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.add_delete_callback(self.uninstall)
        self.recurring_action("_monitor", 600)

    def _monitor(self):
        try:
            self.state.check("actions", "install", "ok")
        except StateCheckError:
            return

        for s in self.node_sal.client.rtinfo.list():
            if s.address == self.data["address"] and s.port == self.data["port"]:
                return

        self.node_sal.client.rtinfo.start(
            self.data["address"], self.data["port"], self.data["disks"]
        )

    @property
    def node_sal(self):
        return j.clients.zos.get(NODE_CLIENT)

    def install(self):
        # reinstall if already present
        # stop doesn't throw exception when no service with address/port is present
        self.node_sal.client.rtinfo.stop(self.data["address"], self.data["port"])

        self.node_sal.client.rtinfo.start(
            self.data["address"], self.data["port"], self.data["disks"]
        )

        self.state.set("actions", "install", "ok")

    def uninstall(self):
        self.node_sal.client.rtinfo.stop(self.data["address"], self.data["port"])
        self.state.delete("actions", "install")
