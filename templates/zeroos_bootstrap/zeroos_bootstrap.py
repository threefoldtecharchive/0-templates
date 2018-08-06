from gevent import sleep

from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import timeout
from zerorobot.template.state import StateCheckError

NODE_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/node/0.0.1'
ERP_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/erp_registeration/0.0.1'
HARDWARE_CHECK_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/hardware_check/0.0.1'


class ZeroosBootstrap(TemplateBase):

    version = '0.0.1'
    template_name = "zeroos_bootstrap"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)

        # start recurring action
        self.recurring_action('bootstrap', 10)

    def validate(self):
        if not self.data['zerotierClient']:
            raise RuntimeError("no zerotier instance specified")

        if self.data['networks']:
            for name in self.data['networks']:
                # validate the network service on which we depend actually exists
                self.api.services.get(name=name)

    @property
    def _zt(self):
        return j.clients.zerotier.get(self.data['zerotierClient'])

    def bootstrap(self):
        self.logger.info("start discovering new members")

        netid = self.data['zerotierNetID']

        resp = self._zt.client.network.listMembers(netid)
        members = resp.json()

        for member in members:
            try:
                self._add_node(member)
            except Exception as err:
                self.logger.error(str(err))
                self._unauthorize_member(member)

    def _authorize_member(self, member):
        self.logger.info("authorize new member %s", member['nodeId'])
        netid = self.data['zerotierNetID']
        member['config']['authorized'] = True
        self._zt.client.network.updateMember(member, member['nodeId'], netid)

    def _unauthorize_member(self, member):
        self.logger.info("unauthorize new member %s", member['nodeId'])
        netid = self.data['zerotierNetID']
        member['config']['authorized'] = False
        self._zt.client.network.updateMember(member, member['nodeId'], netid)

    @timeout(20, error_message='Node did not get an ip assigned')
    def _wait_member_ip(self, member):
        self.logger.info("wait ip for member %s", member['nodeId'])
        netid = self.data['zerotierNetID']

        resp = self._zt.client.network.getMember(member['nodeId'], netid)
        member = resp.json()

        while True:
            self.logger.info('Checking ip assignments for node with id %s' % member['nodeId'])
            if len(member['config']['ipAssignments']):
                break
            sleep(1)
            resp = self._zt.client.network.getMember(member['nodeId'], netid)
            member = resp.json()

        zerotier_ip = member['config']['ipAssignments'][0]
        return zerotier_ip

    def _get_node_sal(self, ip, timeout=120):
        instance = 'bootstrap'
        j.clients.zos.delete(instance)

        data = {
            'host': ip,
            'port': 6379,
            'password_': self.data.get('redisPassword', ''),
            'db': 0,
            'ssl': True,
            'timeout': timeout,
        }

        # ensure client config
        # get a node object from the zero-os SAL
        node = j.clients.zos.get(
            instance=instance,
            data=data,
            create=True,
            die=True,
            interactive=False)

        node.client.config.save()

        return node

    @timeout(60, error_message="can't connect, unauthorizing member")
    def _ping_node(self, node_sal, zerotier_ip):
        self.logger.info("connection to g8os with IP: %s", zerotier_ip)
        while True:
            try:
                node_sal.client.ping()
                break
            except Exception as e:
                continue

    def _add_node(self, member):
        if not member['online'] or member['config']['authorized']:
            return

        netid = self.data['zerotierNetID']

        # authorized new member
        self._authorize_member(member)

        # get assigned ip of this member
        zerotier_ip = self._wait_member_ip(member)

        # create client configuration for that node, to test the connection
        node_sal = self._get_node_sal(zerotier_ip, timeout=10)
        self._ping_node(node_sal, zerotier_ip)

        # create client configuration for that node, to start installing it
        node_sal = self._get_node_sal(zerotier_ip, timeout=120)

        for hw_check in self.api.services.find(template_uid=HARDWARE_CHECK_TEMPLATE_UID):
            hw_check.schedule_action('register', args={'node_name': node_sal.name}).wait(die=True)

        # connection succeeded, set the hostname of the node to zerotier member
        name = node_sal.name
        member['name'] = name
        member['description'] = node_sal.client.info.os().get('hostname', '')
        member['config']['authorized'] = True  # make sure we don't unauthorize
        self._zt.client.network.updateMember(member, member['nodeId'], netid)

        # TODO: this should be configurable
        results = self.api.services.find(template_name='node', name=name)
        if len(results) > 0:
            # the node already exists
            self.logger.info("service for node %s already exists, updating model", name)
            node = results[0]
            try:
                node.state.check('actions', 'install', 'ok')
                node.schedule_action('update_data', args={'data': {'redisAddr': zerotier_ip}})
                return
            except StateCheckError:
                # node wasn't installed properly let's start from scratch
                node.delete()

        # create and install the node.zero-os service
        if self.data['wipeDisks']:
            self.logger.info("wipe disk")
            node_sal.wipedisks()

        hostname = node_sal.client.info.os()['hostname']
        if hostname == 'zero-os':
            hostname = 'zero-os-%s' % name

        data = {
            'status': 'running',
            'networks': self.data.get('networks', []),
            'hostname': hostname,
            'redisAddr': zerotier_ip,
            'redisPassword': self.data.get('redisPassword', ''),
        }
        self.logger.info("create node.zero-os service {}".format(name))
        node = self.api.services.create(NODE_TEMPLATE_UID, name, data=data)
        task_install = node.schedule_action('install')

        try:
            task_install.wait(120)
        except TimeoutError as err:
            self.logger.error("node %s took too long to install", name)
            node.delete()
            raise err
        if task_install.state == 'error':
            node.delete()
            raise RuntimeError(
                "unexpected error during installation of node %s: %s" % (name, task_install.eco.errormessage))

        for erp in self.api.services.find(template_uid=ERP_TEMPLATE_UID):
            erp.schedule_action('register', args={'node_name': name}).wait(die=True)

    def delete_node(self, redis_addr):
        """
        this method will be called from the node.zero-os to remove the node from zerotier
        """
        netid = self.data['zerotierNetID']
        resp = self._zt.client.network.listMembers(netid)
        members = resp.json()

        for member in members:
            if redis_addr in member['config']['ipAssignments']:
                self._unauthorize_member(member)
