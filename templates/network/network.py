
import re

import netaddr
from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry, timeout
from zerorobot.template.state import StateCheckError

ALERTA_UID = 'github.com/threefoldtech/0-templates/alerta/0.0.1'
NODE_CLIENT = 'local'


class Network(TemplateBase):

    version = '0.0.1'
    template_name = 'network'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.add_delete_callback(self.uninstall)
        self.recurring_action('_monitor', 30)  # every 30 seconds

    def validate(self):
        cidr = self.data.get('cidr')
        if cidr:
            netaddr.IPNetwork(cidr)

        vlan = self.data.get('vlan')
        if not vlan:
            raise ValueError('Network should have vlan configured')

        if not isinstance(vlan, int):
            raise ValueError('vlan should be an integer')

    @property
    def _node_sal(self):
        """
        connection to the node
        """
        return j.clients.zos.get(NODE_CLIENT)

    def _monitor(self):
        """
        Run a connection test to a destination node. If node
        is not reachable a selfhealing action is going to be taken
        """

        try:
            self.state.check('actions', 'install', 'ok')
        except StateCheckError:
            return

        hostname = self._node_sal.client.info.os()['hostname']
        node_id = self._node_sal.name
        data = {
            'attributes': {},
            'resource': hostname,
            'environment': 'Production',
            'severity': 'critical',
            'event': 'Network',
            'tags': ["node:%s" % hostname, "node_id:%s" % node_id],
            'service': [self.template_uid.name]
        }

        nics_by_name = {n['name']: n for n in self._node_sal.client.info.nic()}
        for nic_name in self.data['usedInterfaces']:
            if nic_name not in nics_by_name:
                data['text'] = "interface %s not found" % nic_name
                send_alert(self.api.services.find(template_uid=ALERTA_UID), data)
            elif 'up' not in nics_by_name[nic_name]['flags']:
                data['text'] = "interface %s is down" % nic_name
                data['tags'].append('interface:%s' % nic_name)
                send_alert(self.api.services.find(template_uid=ALERTA_UID), data)
            elif 'carrier' in nics_by_name[nic_name] and nics_by_name[nic_name]['carrier'] is False:
                data['text'] = "interface %s has no carrier" % nic_name
                data['tags'].append('interface:%s' % nic_name)
                send_alert(self.api.services.find(template_uid=ALERTA_UID), data)

    def configure(self):
        self.logger.info('installing network %s' % self.name)

        nics_by_name = {n['name']: n for n in self._node_sal.client.ip.link.list()}
        if 'backplane' in nics_by_name and nics_by_name['backplane'].get('up', False):
            return

        driver = self.data.get('driver')
        if driver:
            self.logger.info("reload driver {}".format(driver))
            self._node_sal.network.reload_driver(driver)

        self.logger.info("configure network: cidr: {cidr} - vlan tag: {vlan}".format(**self.data))
        self.data['usedInterfaces'] = self._node_sal.network.configure(
            cidr=self.data['cidr'],
            vlan_tag=self.data['vlan'],
            ovs_container_name='ovs',
            bonded=self.data.get('bonded', False),
            mtu=self.data.get('mtu', 9000) or 9000,
            mode=self.data.get('mode', 'ovs'),
            interfaces=self.data.get('interfaces').copy() or None,
        )

        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        self._node_sal.network.unconfigure('ovs', self.data.get('mode', 'ovs'))
        self.data['usedInterfaces'] = []
        self.state.delete('actions', 'install')


def send_alert(alertas, alert):
    for alerta in alertas:
        alerta.schedule_action('send_alert', args={'data': alert})
