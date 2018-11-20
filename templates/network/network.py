
from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry, timeout
from zerorobot.template.state import StateCheckError
import netaddr
import re

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
        for nic in self.data['usedInterfaces']:
            if j.sal.nettools.isNicConnected(nic):
                continue
            data = {
                'attributes': {},
                'resource': hostname,
                'text': 'network interface %s is down' % nic,
                'environment': 'Production',
                'severity': 'critical',
                'event': 'Network',
                'tags': ["node:%s" % hostname, "node_id:%s" % node_id, "interface:%s" % nic],
                'service': [self.template_uid.name]
            }
            send_alert(self.api.services.find(template_uid='github.com/threefoldtech/0-templates/alerta/0.0.1'), data)

    def configure(self):
        self.logger.info('installing network %s' % self.name)

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
        )

        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        self._node_sal.network.unconfigure('ovs', self.data.get('mode', 'ovs'))
        self.data['usedInterfaces'] = []
        self.state.delete('actions', 'install')


def send_alert(alertas, alert):
    for alerta in alertas:
        alerta.schedule_action('send_alert', args={'data': alert})
