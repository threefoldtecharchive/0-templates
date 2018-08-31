import requests
import os
import socket
import psutil
from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.server import auth

NODE_CLIENT = 'local'


class PortalConnection(TemplateBase):

    version = '0.0.1'
    template_name = 'portal_connection'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)

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

    def install(self, username="", password=""):
        auth_token = self._authenticate(username, password)

        robot_ip, robot_port = self._get_listen_address()
        cookies = {"beaker.session.id": auth_token}
        data = {
            'name': self._node_sal.name,
            'url': "http://{ip}:{port}".format(ip=robot_ip, port=robot_port),
            'godToken': auth.god_jwt.create()
        }
        resp = requests.post("{base_url}/restmachine/zrobot/client/add".format(base_url=self.data['url']), json=data, cookies=cookies)
        resp.raise_for_status()

        self.state.set('actions', 'install', 'ok')

    def _get_listen_address(self):
        r_pid = os.getpid()
        self.logger.info('Robot pid = %s' % r_pid)
        for c in psutil.net_connections('inet'):
            self.logger.info('Connection pid=%s, type=%s, status=%s' % (c.pid, c.type, c.status))
            if c.pid == r_pid and c.type == socket.SOCK_STREAM and c.status == psutil.CONN_LISTEN:
                return c.laddr
        raise RuntimeError("Could not determine listening address")

    def uninstall(self, username, password):
        auth_token = self._authenticate(username, password)
        cookies = {"beaker.session.id": auth_token}

        data = {'name': self._node_sal.name}
        resp = requests.post("{base_url}/restmachine/zrobot/client/delete".format(base_url=self.data['url']), json=data, cookies=cookies)
        resp.raise_for_status()

        self.state.delete('actions', 'install')

    def _authenticate(self, username, password):
        resp = requests.post(
            "{base_url}/restmachine/system/usermanager/authenticate".format(base_url=self.data['url']),
            params={"name":username, "secret":password})
        resp.raise_for_status()
        auth_token = resp.json()
        return auth_token
