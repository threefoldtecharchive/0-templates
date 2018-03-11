from js9 import j

from zerorobot.template.base import TemplateBase

CONTAINER_TEMPLATE_UID = 'github.com/zero-os/0-templates/container/0.0.1'
EXPLORER_FLIST = 'https://hub.gig.tech/<path>'


class BlockCreator(TemplateBase):
    version = '0.0.1'
    template_name = 'explorer'

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)

    @property
    def node_sal(self):
        return j.clients.zero_os.sal.node_get(self.data['node'])

    @property
    def container_sal(self):
        return self.node_sal.containers.get(self.data['container'])

    def install(self):
        """
        Creating explorer container with the provided flist, and configure mounts for datadirs
        """
        raise NotImplementedError

    def start(self):
        """
        start both explorer daemon and caddy
        """
        raise NotImplementedError
