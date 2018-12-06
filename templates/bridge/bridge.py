
from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError
import netaddr

NODE_CLIENT = 'local'


class Bridge(TemplateBase):

    version = '0.0.1'
    template_name = 'bridge'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.add_delete_callback(self.uninstall)

    def validate(self):
        mac = self.data.get("hwaddr")
        if mac and not netaddr.valid_mac(mac):
            raise ValueError("hwAddr %s is not valid" % mac)

        mode = self.data.get('mode')
        if not mode:
            raise ValueError("mode need to be specified")
        if mode not in ['none', 'static', 'dnsmasq']:
            raise ValueError("mode must be one of 'none','static','dnsmasq'")

    @property
    def _node_sal(self):
        """
        connection to the node
        """
        return j.clients.zos.get(NODE_CLIENT)

    def install(self):
        try:
            self.state.check('actions', 'install', 'ok')
            return
        except StateCheckError:
            pass

        self.logger.info('install bridge %s', self.name)
        network = self.data['mode'] if self.data['mode'] != 'none' else None
        self._node_sal.client.bridge.create(
            name=self.name,
            hwaddr=self.data['hwaddr'],
            network=network,
            nat=self.data.get('nat', False),
            settings=self.data.get('settings', None),
        )

        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        self.logger.info('delete bridge %s', self.name)
        if self.name in self._node_sal.client.bridge.list():
            self._node_sal.client.bridge.delete(self.name)

        self.state.delete('actions', 'install')

    def nic_add(self, nic):
        self.state.check('actions', 'install', 'ok')
        self._node_sal.client.bridge.nic_add(self.name, nic)

    def nic_remove(self, nic):
        self.state.check('actions', 'install', 'ok')
        if nic in self._node_sal.client.bridge.nic_list():
            self._node_sal.client.bridge.nic_remove(nic)

    def nic_list(self):
        self.state.check('actions', 'install', 'ok')
        return self._node_sal.client.bridge.nic_list(self.name)
