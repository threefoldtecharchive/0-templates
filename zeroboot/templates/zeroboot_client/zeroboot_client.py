from js9 import j

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
        network_id = self.data.get('networkId')
        if not network_id:
            raise ValueError("no networkId specified in service data")

        sshClient = self.data.get('sshClient')
        if not network_id:
            raise ValueError("no sshClient specified in service data")

        zerotierClient = self.data.get('zerotierClient')

        # this will create a configuration for this instance
        data = {
            'network_id': network_id,
            'sshclient_instance': sshClient,
            'zerotier_instance': zerotierClient,
        }
        _ = j.clients.zboot.get(self.name, data=data, interactive=False)

    def delete(self):
        """
        delete the client configuration
        """
        j.clients.ssh.delete(self.name)
        # call the delete of the base class
        super().delete()
