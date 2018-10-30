from jumpscale import j
from urllib.parse import urlparse
from zerorobot.template.base import TemplateBase

ZT_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/zerotier_client/0.0.1'


class ZerotierClient(TemplateBase):

    version = '0.0.1'
    template_name = "zerotier_client"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.add_delete_callback(self.uninstall)

        # client instance already exists
        if self.name in j.clients.zerotier.list():
            return

        # create the client instance
        token = self.data.get('token')
        if not token:
            raise ValueError("no token specified in service data")

        # this will create a configuration for this instance
        j.clients.zerotier.get(self.name, data={'token_': self.data['token']})

    def uninstall(self):
        """
        uninstall the client configuration
        """
        j.clients.zerotier.delete(self.name)

    def token(self):
        return self.data['token']

    def _get_remote_robot(self, url):
        robotname = urlparse(url).netloc
        return self.api.robots.get(robotname, url)

    def add_to_robot(self, url, name):
        robotapi = self._get_remote_robot(url)
        robotapi.services.find_or_create(ZT_TEMPLATE_UID, service_name=name, data={'token': self.data['token']})

    def remove_from_robot(self, url, name):
        robotapi = self._get_remote_robot(url)
        for service in robotapi.services.find(template_uid=ZT_TEMPLATE_UID, name=name):
            service.delete()
