from js9 import j

from zerorobot.template.base import TemplateBase

class IpmiClient(TemplateBase):

    version = '0.0.1'
    template_name = "ipmi_client"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)

    def validate(self):
        # client instance already exists
        if self.name in j.clients.zboot.list():
            return

        # create the client instance
        bmc = self.data.get('bmc')
        if not bmc:
            raise ValueError("no bmc specified in service data")
        user = self.data.get('user')
        if not user:
            raise ValueError("no user specified in service data")
        password = self.data.get('password')
        if not password:
            raise ValueError("no password specified in service data")

        data = {
            'bmc': bmc,
            'user': user,
            'password_': password,
            'port': self.data.get('port')
        }
        _ = j.clients.ipmi.get(instance=self.name, data=data, interactive=False)

    def delete(self):
        """
        delete the client configuration
        """
        j.clients.ipmi.delete(self.name)
        # call the delete of the base class
        super().delete()
