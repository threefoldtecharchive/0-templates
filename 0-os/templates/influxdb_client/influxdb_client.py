
from js9 import j
from zerorobot.template.base import TemplateBase

class InfluxdbClient(TemplateBase):
    version = '0.0.1'
    template_name = 'influxdb_client'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)

    def install(self):
        self.influxdb = j.clients.influxdb.get(
            self.name,
            data={
            'host' : self.data['host'],
            'password':self.data['passwd'],
            'port' : self.data['port'],
            'ssl' : self.data['ssl'],
            'username' : self.data['login'],
            'verify_ssl' : self.data['verifySsl']})
        self.state.set('actions', 'install', 'ok')

    def delete(self):
        self.influxdb = j.clients.influxdb.delete(self.name)
        self.state.delete('actions', 'install')