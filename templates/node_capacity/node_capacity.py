import time

from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry, timeout
from zerorobot.template.state import StateCheckError


class NodeCapacity(TemplateBase):

    version = "0.0.1"
    template_name = "node_capacity"

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.recurring_action("_total", 10 * 60)  # every 10 minutes
        self.recurring_action("_reality", 10 * 60)  # every 10 minutes
        self.recurring_action("_reserved", 10 * 60)  # every 10 minutes
        self._node_sal = self.api.node_sal

    @timeout(300)
    def _total(self):
        """
        register the total node capacity
        """
        self.logger.info("register the total node capacity")

        node = self.api.services.get(template_account="threefoldtech", template_name="node")
        node.state.check("disks", "mounted", "ok")

        self.state.delete("capacity", "total")

        send_hardware = False
        last_update = self.data.get('lastHardwareUpdate')
        # check if we sent hardware update more then 24h ago
        if not last_update or (int(time.time()) - last_update > 86400):
            send_hardware = True

        try:
            try:
                self._node_sal.capacity.register(include_hardware_dump=send_hardware)
                self.state.set("capacity", "total", "ok")
                self.data['lastHardwareUpdate'] = int(time.time())
            except TypeError as err:
                self.logger.error("fail to send hardware update, need to update 0-robot flist")
                self._node_sal.capacity.register()
                self.state.set("capacity", "total", "ok")
        except:
            self.state.set("capacity", "total", "error")
            raise

    @timeout(300)
    def _reserved(self):
        """
        update the reserved capacity of the node
        """
        self.logger.info("update the reserved capacity of the node")
        try:
            self._node_sal.capacity.update_reserved(
                vms=self.api.services.find(template_name="vm", template_account="threefoldtech"),
                vdisks=self.api.services.find(template_name="vdisk", template_account="threefoldtech"),
                gateways=self.api.services.find(template_name="gateway", template_account="threefoldtech"),
            )
            self.state.set("capacity", "reserved", "ok")
        except:
            self.state.set("capacity", "reserved", "error")
            raise

    @timeout(300)
    def _reality(self):
        """
        update the real used capacity of the node
        """
        self.logger.info("update the real used capacity of the node")
        try:
            self._node_sal.capacity.update_reality()
            self.state.set("capacity", "reality", "ok")
        except:
            self.state.set("capacity", "reality", "error")
            raise
