import requests
from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.server import auth

NODE_CLIENT = 'local'


class PortalConnection(TemplateBase):

    version = '0.0.1'
    template_name = 'portal_connection'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.add_delete_callback(self.uninstall)

    def validate(self):
        for param in ['url']:
            if not self.data[param]:
                raise ValueError("parameter '%s' needs to be set" % (param))

    @property
    def _node_sal(self):
        """
        connection to the local node
        """
        return j.clients.zos.get(NODE_CLIENT)

    def install(self):
        data = {
            'name': self._node_sal.name,
            'url': self._node_sal,
            'godToken': auth.god_jwt.create()
        }
        resp = requests.post(self.data['url'], json=data)
        resp.raise_for_status()

        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        data = {'name': self._node_sal.name}
        resp = requests.post(self.data['url'], json=data)
        resp.raise_for_status()

        self.state.delete('actions', 'install')
