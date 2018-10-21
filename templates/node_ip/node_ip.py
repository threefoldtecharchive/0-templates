
from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError
import netaddr

NODE_CLIENT = 'local'


class NodeIp(TemplateBase):

    version = '0.0.1'
    template_name = 'node_ip'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)

    def validate(self):
        cidr = self.data.get('cidr')
        if not cidr:
            raise ValueError('interface should be provided')

        try:
            netaddr.IPNetwork(cidr)
        except netaddr.AddrFormatError:
            raise ValueError('cidr format is not valid')

        vlan = self.data.get('interface')
        if not vlan:
            raise ValueError('interface should be provided')

    def _node_sal(self):
        """
        connection to the node
        """
        return j.clients.zos.get(NODE_CLIENT)

    def install(self):
        node = self._node_sal()
        interface = self.data['interface']
        cidr = self.data['address']

        ips = node.client.ip.list(cidr)
        if cidr not in ips:
            node.client.ip.addr.add(interface, cidr)

    def uninstall(self):
        node = self._node_sal()
        interface = self.data['interface']
        cidr = self.data['address']

        ips = node.client.ip.list(cidr)
        if cidr in ips:
            node.client.ip.addr.delete(interface, cidr)
