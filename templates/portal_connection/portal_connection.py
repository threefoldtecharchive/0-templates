import requests
import os
import socket
import psutil
from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.server import auth


class PortalConnection(TemplateBase):

    version = "0.0.1"
    template_name = "portal_connection"

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self._node_sal = self.api.node_sal

    def validate(self):
        for param in ["url", "username", "password"]:
            if not self.data[param]:
                raise ValueError("parameter '%s' needs to be set" % (param))

    def install(self):
        auth_token = _authenticate(self.data["username"], self.data["password"], self.data["url"])

        cookies = {"beaker.session.id": auth_token}
        data = {
            "name": self._node_sal.name,
            "url": "http://%s:6600" % self._node_sal.management_address,
            "godToken": auth.god_jwt.create(),
            "username": self._node_sal.client.info.os()["hostname"],
        }
        resp = requests.post(
            "{base_url}/restmachine/zrobot/client/add".format(base_url=self.data["url"]), json=data, cookies=cookies
        )
        if resp.status_code == 409:
            if not "already in the portal" in resp.text:
                resp.raise_for_status()
            else:
                self.logger.info(resp.content)

        self.state.set("actions", "install", "ok")

    def uninstall(self):
        auth_token = _authenticate(self.data["username"], self.data["password"], self.data["url"])
        cookies = {"beaker.session.id": auth_token}

        data = {"name": self._node_sal.name}
        resp = requests.post(
            "{base_url}/restmachine/zrobot/client/delete".format(base_url=self.data["url"]), json=data, cookies=cookies
        )
        resp.raise_for_status()

        self.state.delete("actions", "install")


def _authenticate(username, password, url):
    resp = requests.post(
        "{base_url}/restmachine/system/usermanager/authenticate".format(base_url=url),
        params={"name": username, "secret": password},
    )
    resp.raise_for_status()
    auth_token = resp.json()
    return auth_token
