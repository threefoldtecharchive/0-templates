from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError
from zerorobot.service_collection import ServiceNotFoundError

ZERODB_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/zerodb/0.0.1'


class Namespace(TemplateBase):

    version = '0.0.1'
    template_name = 'namespace'

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.add_delete_callback(self.uninstall)
        if not self.data.get('password'):
            self.data['password'] = j.data.idgenerator.generateXCharID(32)
        self.recurring_action('_monitor', 30)  # every 30 seconds

    def validate(self):
        self.state.delete('status', 'running')
        try:
            # ensure that a node service exists
            node = self.api.services.get(template_account='threefoldtech', template_name='node')
            node.state.check('actions', 'install', 'ok')
        except:
            raise RuntimeError("Node service not found, can't install the namespace")

        for param in ['diskType', 'size', 'mode']:
            if not self.data.get(param):
                raise ValueError("parameter '{}' not valid: {}".format(param, str(self.data[param])))

    def _monitor(self):
        self.logger.info('Monitor namespace %s' % self.name)
        try:
            self.state.check('actions', 'install', 'ok')
        except StateCheckError:
            return

        if not self.data['zerodb']:
            # Reinstall on a different zerodb
            self.state.delete('status', 'running')
            self.install()

        try:
            self._zerodb.state.check('status', 'running', 'ok')
            self.state.set('status', 'running', 'ok')
        except StateCheckError:
            self.logger.info('Zerodb is not reachable anymore, installing namespace on a different zerodb')
            # Reinstall on a different zerodb
            self.data['zerodb'] = ''
            self.state.delete('status', 'running')
            self.install()

    @property
    def _zerodb(self):
        return self.api.services.get(template_uid=ZERODB_TEMPLATE_UID, name=self.data['zerodb'])

    def install(self):
        try:
            # no op is already installed
            self.state.check('actions', 'install', 'ok')
            if self.data['zerodb']:
                return
        except StateCheckError:
            pass

        node = self.api.services.get(template_account='threefoldtech', template_name='node')
        kwargs = {
            'disktype': self.data['diskType'],
            'mode': self.data['mode'],
            'password': self.data['password'],
            'public': self.data['public'],
            'ns_size': self.data['size'],
            'name': self.data['nsName'],
        }
        # use the method on the node service to create the zdb and the namespace.
        # this action hold the logic of the capacity planning for the zdb and namespaces
        self.data['zerodb'], self.data['nsName'] = node.schedule_action('create_zdb_namespace', kwargs).wait(die=True).result
        self.state.set('actions', 'install', 'ok')

    def info(self):
        self.state.check('actions', 'install', 'ok')
        return self._zerodb.schedule_action('namespace_info', args={'name': self.data['nsName']}).wait(die=True).result

    def url(self):
        self.state.check('actions', 'install', 'ok')
        return self._zerodb.schedule_action('namespace_url', args={'name': self.data['nsName']}).wait(die=True).result

    def private_url(self):
        self.state.check('actions', 'install', 'ok')
        return self._zerodb.schedule_action('namespace_private_url', args={'name': self.data['nsName']}).wait(die=True).result

    def uninstall(self):
        self._zerodb.schedule_action('namespace_delete', args={'name': self.data['nsName']}).wait(die=True)
        self.state.delete('actions', 'install')

    def connection_info(self):
        self.state.check('actions', 'install', 'ok')
        return self._zerodb.schedule_action('connection_info').wait(die=True).result
