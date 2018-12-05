
from Jumpscale import j
from zerorobot.template.base import TemplateBase


class InfluxdbClient(TemplateBase):
    version = '0.0.1'
    template_name = 'influxdb_client'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.add_delete_callback(self.uninstall)

    def install(self):
        self.influxdb = j.clients.influxdb.get(
            self.name,
            data={
                'host': self.data['host'],
                'password': self.data['passwd'],
                'port': self.data['port'],
                'ssl': self.data['ssl'],
                'username': self.data['login'],
                'verify_ssl': self.data['verifySsl']
            })
        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        self.influxdb = j.clients.influxdb.delete(self.name)
        self.state.delete('actions', 'install')

