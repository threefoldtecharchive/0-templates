from jumpscale import j

from zerorobot.template.base import TemplateBase

class ZerobootClient(TemplateBase):

    version = '0.0.1'
    template_name = "zeroboot_client"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)

    def validate(self):
        # client instance already exists
        if self.name in j.clients.zboot.list():
            return

        # create the client instance
        sshClient = self.data.get('sshClient')
        if not sshClient:
            raise ValueError("no sshClient specified in service data")

        # this will create a configuration for this instance
        data = {
            'network_id': self.data.get("networkId") or "",
            'sshclient_instance': sshClient,
            'zerotier_instance': self.data.get('zerotierClient') or "",
        }
        j.clients.zboot.get(self.name, data=data, interactive=False)

    def delete(self):
        """
        delete the client configuration
        """
        j.clients.ssh.delete(self.name)
        # call the delete of the base class
        super().delete()
