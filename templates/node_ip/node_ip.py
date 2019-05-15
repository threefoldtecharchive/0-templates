from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError
import netaddr


class NodeIp(TemplateBase):

    version = "0.0.1"
    template_name = "node_ip"

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.recurring_action("_monitor", 60)  # every 60 seconds
        self._node_sal = self.api.node_sal

    def validate(self):
        cidr = self.data.get("cidr")
        if not cidr:
            raise ValueError("cidr should be provided")

        try:
            netaddr.IPNetwork(cidr)
        except netaddr.AddrFormatError:
            raise ValueError("cidr format is not valid")

        vlan = self.data.get("interface")
        if not vlan:
            raise ValueError("interface should be provided")

    def _monitor(self):
        try:
            self.state.check("actions", "install", "ok")
        except StateCheckError:
            return

        self.install()

    def install(self):
        interface = self.data["interface"]
        cidr = self.data["cidr"]
        gateway = self.data.get("gateway")

        ips = self._node_sal.client.ip.addr.list(interface)
        if cidr not in ips:
            self.logger.info("config ip %s on interface %s", cidr, interface)
            self._node_sal.client.ip.addr.add(interface, cidr)

        if gateway:
            routes = self._node_sal.client.ip.route.list()
            if {"dev": interface, "dst": "", "gw": gateway} not in routes:
                self._node_sal.client.bash("ip r del default; ip r add default via %s" % gateway)

        self.state.set("actions", "install", "ok")

    def uninstall(self):
        interface = self.data["interface"]
        cidr = self.data["cidr"]

        ips = self._node_sal.client.ip.addr.list(interface)
        if cidr in ips:
            self._node_sal.client.ip.addr.delete(interface, cidr)
        self.state.delete("actions", "install")
