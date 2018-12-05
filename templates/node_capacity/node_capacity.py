
from Jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry, timeout
from zerorobot.template.state import StateCheckError


NODE_CLIENT = 'local'


class NodeCapacity(TemplateBase):

    version = '0.0.1'
    template_name = 'node_capacity'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.recurring_action('_total', 10 * 60)   # every 10 minutes
        self.recurring_action('_reality', 10 * 60)      # every 10 minutes
        self.recurring_action('_reserved', 10 * 60)  # every 10 minutes

    @property
    def _node_sal(self):
        """
        connection to the node
        """
        return j.clients.zos.get(NODE_CLIENT)

    @timeout(300)
    def _total(self):
        """
        register the total node capacity
        """
        self.logger.info("register the total node capacity")

        self.state.delete('capacity', 'total')
        try:
            self._node_sal.capacity.register()
            self.state.set('capacity', 'total', 'ok')
        except:
            self.state.set('capacity', 'total', 'error')
            raise

    @timeout(300)
    def _reserved(self):
        """
        update the reserved capacity of the node
        """
        self.logger.info("update the reserved capacity of the node")
        try:
            self._node_sal.capacity.update_reserved(
                vms=self.api.services.find(template_name='vm', template_account='threefoldtech'),
                vdisks=self.api.services.find(template_name='vdisk', template_account='threefoldtech'),
                gateways=self.api.services.find(template_name='gateway', template_account='threefoldtech'),
            )
            self.state.set('capacity', 'reserved', 'ok')
        except:
            self.state.set('capacity', 'reserved', 'error')
            raise

    @timeout(300)
    def _reality(self):
        """
        update the real used capacity of the node
        """
        self.logger.info("update the real used capacity of the node")
        try:
            self._node_sal.capacity.update_reality()
            self.state.set('capacity', 'reality', 'ok')
        except:
            self.state.set('capacity', 'reality', 'error')
            raise

