from js9 import j

from zerorobot.template.base import TemplateBase

class SshClient(TemplateBase):

    version = '0.0.1'
    template_name = "ssh_client"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)

    def validate(self):
        # client instance already exists
        if self.name in j.clients.ssh.list():
            return

        # create the client instance
        host = self.data.get('host')
        if not host:
            raise ValueError("no host specified in service data")

        # this will create a configuration for this instance
        data = {
            'addr': host,
            'port': self.data.get('port'),
            'login': self.data.get('login'),
            'passwd_': self.data.get('password'),
        }
        _ = j.clients.ssh.get(self.name, data=data, interactive=False)

    def delete(self):
        """
        delete the client configuration
        """
        j.clients.ssh.delete(self.name)
        # call the delete of the base class
        super().delete()
