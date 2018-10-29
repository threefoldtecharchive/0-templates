
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

    def _can_ping(self):
        """
        The test is simply pinging the test ip as follows

        optimal is `ping -c 4 -W 1 -i 0.1 -nq <ip>` but busybox ping doesn't have -i flag
        so we do `ping -c r -W 1 -nq <ip>` instead
        """

        def ping(test_ip):
            result = self._node_sal.client.system('ping -c r -W 1 -nq "%s"' % test_ip).get()
            if result.state != 'SUCCESS':
                # no need to parse output, we know network is not working
                return False

            match = re.search(
                r'^(\d+) packets transmitted, (\d+) packets received, (\d+)% packet loss$',
                result.stdout,
                re.MULTILINE
            )

            if match is None:
                self.logger.error('failed to parse ping output')
                return True  # avoid taking action to not disturb network until the parser is fixed

            return not bool(match.group(3))  # percentage, 0 is good, anything else is bad

        ips = self.data.get('testIps', [])
        if not ips:
            return True  # assume network is working

        for ip in ips:
            if ping(ip):
                return True
        return False

    def _restart_bond(self):
        self._node_sal.network.restart_bond(
            ovs_container_name='ovs',
            bond='bond0',
        )

    def _monitor(self):
        """
        Run a connection test to a destination node. If node
        is not reachable a selfhealing action is going to be taken
        """

        try:
            self.state.check('actions', 'install', 'ok')
        except StateCheckError:
            return

        if not self.data.get('bonded', False):
            # the check is only for bonded interfaces
            return
        mode = self.data.get('mode', 'ovs')
        if mode and mode != 'ovs':
            # only monitor in case of ovs
            return

        if not self._can_ping():
            ips = ','.join(self.data.get('testIps', []))
            self.logger.info('cannot ping test ips %s. restarting bond slaves' % ips)
            self._restart_bond()

    def configure(self):
        self.logger.info('installing network %s' % self.name)

        driver = self.data.get('driver')
        if driver:
            self.logger.info("reload driver {}".format(driver))
            self._node_sal.network.reload_driver(driver)

        self.logger.info("configure network: cidr: {cidr} - vlan tag: {vlan}".format(**self.data))
        self._node_sal.network.configure(
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
        self.state.delete('actions', 'install')
