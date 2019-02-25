
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
            'environment': 'Production',
            'severity': 'warning',
            'event': 'Network',
            'tags': ["node:%s" % hostname, "node_id:%s" % node_id],
            'service': [self.template_uid.name]
        }

        nics_by_name = {n['name']: n for n in self._node_sal.client.info.nic()}
        nics_status = {name: {'healthy': True} for name in self.data['usedInterfaces']}

        for nic_name in self.data['usedInterfaces']:
            alert_data = data.copy()
            alert_data['resource'] = "%s-%s" % (hostname, nic_name)
            alert_data['severity'] = 'critical' if nic_name == 'backplane' else 'warning'
            alert_data['tags'].append('interface:%s' % nic_name)

            if nic_name not in nics_by_name:
                nics_status[nic_name]['healthy'] = False
                alert_data['text'] = "interface %s not found" % nic_name
                send_alert(self.api.services.find(template_uid=ALERTA_UID), alert_data)

            elif 'up' not in nics_by_name[nic_name]['flags']:
                nics_status[nic_name]['healthy'] = False
                alert_data['text'] = "interface %s is down" % nic_name
                send_alert(self.api.services.find(template_uid=ALERTA_UID), alert_data)

            elif 'carrier' in nics_by_name[nic_name] and nics_by_name[nic_name]['carrier'] is False:
                alert_data['text'] = "interface %s has no carrier" % nic_name
                nics_status[nic_name]['healthy'] = False
                send_alert(self.api.services.find(template_uid=ALERTA_UID), alert_data)

        if 'backplane' in nics_status and nics_status['backplane'] is False:
            alert_data = data.copy()
            alert_data['severity'] = 'critical'
            alert_data['text'] = 'backplane is down. Storage network is now offline for this node. Need imediate intervention'
            alert_data['tags'].append('interface:backplane')
            send_alert(self.api.services.find(template_uid=ALERTA_UID), alert_data)
            return

        if 'backplane' in nics_status:
            del nics_status['backplane']

        alert_data = data.copy()
        alert_data['resource'] = "%s network" % (hostname)
        nr_nic_down = [status['healthy'] for status in nics_status.values()].count(False)
        self.logger.info("nr_nic_down %s", nr_nic_down)
        self.logger.info("nics_status %s", nics_status)
        if nr_nic_down == 0:
            return

        if nr_nic_down < len(nics_status):
            alert_data['severity'] = 'major'
            alert_data['text'] = 'Some interfaces used for the storage network are down. But network is still working'
        elif nr_nic_down >= len(nics_status):
            alert_data['severity'] = 'critical'
            alert_data['text'] = 'All interfaces used for the storage network are down. Storage network is now offline for this node, needs imediate intervention'

        for nic_name, status in nics_status.items():
            if not status['healthy']:
                alert_data['tags'].append('interface:%s' % nic_name)
        send_alert(self.api.services.find(template_uid=ALERTA_UID), alert_data)

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
            balance_mode=self.data.get('balanceMode'),
            lacp=self.data.get('lacp', False)
        )

        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        self._node_sal.network.unconfigure('ovs', self.data.get('mode', 'ovs'))
        self.data['usedInterfaces'] = []
        self.state.delete('actions', 'install')


def send_alert(alertas, alert):
    for alerta in alertas:
        alerta.schedule_action('send_alert', args={'data': alert})
