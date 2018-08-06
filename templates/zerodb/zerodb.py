from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError


NODE_TEMPLATE_UID = 'github.com/zero-os/0-templates/node/0.0.1'
NODE_CLIENT = 'local'


class Zerodb(TemplateBase):

    version = '0.0.1'
    template_name = "zerodb"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.recurring_action('_monitor', 10)  # every 10 seconds

    def validate(self):
        self.state.delete('status', 'running')

    @property
    def _node_sal(self):
        # hardcoded local instance, this service is only intended to be install by the node robot
        return j.clients.zos.sal.get_node(NODE_CLIENT)

    @property
    def _zerodb_sal(self):
        data = self.data.copy()
        data['name'] = self.name
        return self._node_sal.primitives.from_dict('zerodb', data)

    def _deploy(self):
        zerodb_sal = self._zerodb_sal
        zerodb_sal.deploy()
        self.data['nodePort'] = zerodb_sal.node_port
        self.data['ztIdentity'] = zerodb_sal.zt_identity

    def _monitor(self):
        self.logger.info('Monitor zerodb %s' % self.name)
        self.state.check('actions', 'install', 'ok')
        self.state.check('actions', 'start', 'ok')

        node = self.api.services.get(template_account='zero-os', template_name='node')
        node.state.check('disks', 'mounted', 'ok')

        if not self._zerodb_sal.is_running()[0]:
            self.state.delete('status', 'running')
            self._zerodb_sal.start()
            if self._zerodb_sal.is_running()[0]:
                self.state.set('status', 'running', 'ok')
        else:
            self.state.set('status', 'running', 'ok')

    def install(self):
        self.logger.info('Installing zerodb %s' % self.name)

        # generate admin password
        if not self.data['admin']:
            self.data['admin'] = j.data.idgenerator.generateXCharID(25)

        self._deploy()
        self.state.set('actions', 'install', 'ok')
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def start(self):
        """
        start zerodb server
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Starting zerodb %s' % self.name)
        self._deploy()
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def stop(self):
        """
        stop zerodb server
        """
        self.logger.info('Stopping zerodb %s' % self.name)

        self._zerodb_sal.stop()
        self.state.delete('actions', 'start')
        self.state.delete('status', 'running')

    def upgrade(self):
        """
        upgrade 0-db
        """
        self.stop()
        self.start()

    def info(self):
        """
        Return disk information
        """
        return self._zerodb_sal.info

    def namespace_list(self):
        """
        List namespace
        :return: list of namespaces ex: ['namespace1', 'namespace2']
        """
        self.state.check('status', 'running', 'ok')
        return self.data['namespaces']

    def namespace_info(self, name):
        """
        Get info of namespace
        :param name: namespace name
        :return: dict
        """
        self.state.check('status', 'running', 'ok')
        if not self._namespace_exists_update_delete(name):
            raise LookupError('Namespace {} doesn\'t exist'.format(name))
        return self._zerodb_sal.namespaces[name].info().to_dict()

    def namespace_url(self, name):
        """
        Get url of the namespace
        :param name: namespace name
        :return: dict
        """
        self.state.check('status', 'running', 'ok')
        if not self._namespace_exists_update_delete(name):
            raise LookupError('Namespace {} doesn\'t exist'.format(name))
        return self._zerodb_sal.namespaces[name].url

    def namespace_private_url(self, name):
        """
        Get private url of the namespace
        :param name: namespace name
        :return: dict
        """
        self.state.check('status', 'running', 'ok')
        if not self._namespace_exists_update_delete(name):
            raise LookupError('Namespace {} doesn\'t exist'.format(name))
        return self._zerodb_sal.namespaces[name].private_url

    def namespace_create(self, name, size=None, password=None, public=True):
        """
        Create a namespace and set the size and secret
        :param name: namespace name
        :param size: namespace size
        :param password: namespace password
        :param public: namespace public status
        """
        self.state.check('status', 'running', 'ok')
        if self._namespace_exists_update_delete(name):
            raise ValueError('Namespace {} already exists'.format(name))
        self.data['namespaces'].append({'name': name, 'size': size, 'password': password, 'public': public})
        self._zerodb_sal.deploy()

    def namespace_set(self, name, prop, value):
        """
        Set a property of a namespace
        :param name: namespace name
        :param prop: property name
        :param value: property value
        """
        self.state.check('status', 'running', 'ok')

        if not self._namespace_exists_update_delete(name, prop, value):
            raise LookupError('Namespace {} doesn\'t exist'.format(name))
        self._zerodb_sal.deploy()

    def namespace_delete(self, name):
        """
        Delete a namespace
        """
        self.state.check('status', 'running', 'ok')
        if not self._namespace_exists_update_delete(name, delete=True):
            return

        self._zerodb_sal.deploy()

    def connection_info(self):
        return {
            'ip': self._node_sal.public_addr,
            'port': self.data['nodePort']
        }

    def _namespace_exists_update_delete(self, name, prop=None, value=None, delete=False):
        if prop and delete:
            raise ValueError('Can\'t set property and delete at the same time')
        if prop and prop not in ['size', 'password', 'public']:
            raise ValueError('Property must be size, password, or public')

        for namespace in self.data['namespaces']:
            if namespace['name'] == name:
                if prop:
                    if prop not in ['size', 'password', 'public']:
                        raise ValueError('Property must be size, password, or public')
                    namespace[prop] = value
                if delete:
                    self.data['namespaces'].remove(namespace)
                return True
        return False
