from js9 import j

from zerorobot.template.base import TemplateBase

class RacktivityClient(TemplateBase):

    version = '0.0.1'
    template_name = "racktivity_client"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)

    def validate(self):
         # client instance already exists
        if self.name in j.clients.racktivity.list():
            return

        # create client instance
        host = self.data.get('host')
        if not host:
            raise ValueError("no host specified in service data")

        data = {
            'username': self.data.get('username'),
            'password_': self.data.get('password'),
            'hostname': host,
            'port': self.data.get('port'),
        }

        _ = j.clients.racktivity.get(self.name, data=data, interactive=False)

    def delete(self):
        """
        delete the client configuration
        """
        j.clients.racktivity.delete(self.name)
        # call the delete of the base class
        super().delete()
