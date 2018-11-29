from jumpscale import j
from io import BytesIO
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry
from zerorobot.template.state import StateCheckError

NODE_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/node/0.0.1'
PORT_MANAGER_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/node_port_manager/0.0.1'
NODE_CLIENT = 'local'


class Zerodb(TemplateBase):

    version = '0.0.1'
    template_name = "zerodb"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        # hardcoded local instance, this service is only intended to be install by the node robot
        self._node_sal = j.clients.zos.get(NODE_CLIENT)
        self.recurring_action('_monitor', 30)  # every 30 seconds

    @property
    def _zerodb_sal(self):
        data = self.data.copy()
        data['name'] = self.name
        return self._node_sal.primitives.from_dict('zerodb', data)

    def _deploy(self):
        zerodb_sal = self._zerodb_sal
        zerodb_sal.deploy()
        self.data['ztIdentity'] = zerodb_sal.zt_identity

    def _monitor_disk(self):
        self.logger.info('Monitor zerodb disk %s' % self.name)
        text_file= BytesIO(b'the string to test write on disk ...')   
        try:
            self._node_sal.client.upload('{}/_monitor_write_disk_test'.format(self.data["path"]), text_file)
            return True
        except Exception:
            return False

    def _monitor(self):
        self.logger.info('Monitor zerodb %s' % self.name)
        try:
            self.state.check('actions', 'install', 'ok')
            self.state.check('actions', 'start', 'ok')
        except StateCheckError:
            return

        node = self.api.services.get(template_account='threefoldtech', template_name='node')
        node.state.check('disks', 'mounted', 'ok')

        data = {
                'attributes': {},
                'resource': self.guid,
                'environment': 'Production',
                'severity': 'critical',
                'event': 'Hardware',
                'tags': [],
                'service': ['zerodb']
            }

        if not self._zerodb_sal.is_running():
            try:
                self._deploy()
            except Exception:
                self.state.delete('status', 'running')
                data['text'] = 'Failed to deploy zerodb {}'.format(self.name)
                send_alert(self.api.services.find(template_uid='github.com/threefoldtech/0-templates/alerta/0.0.1'), data)
                return

            running = self._zerodb_sal.is_running()
            disk_writing = self._monitor_disk()
            if running and disk_writing:
                self.state.set('status', 'running', 'ok')  
            else:
                self.state.delete('status', 'running')
                if not running:
                    data['text'] = 'Failed to start zerodb {}'.format(self.name)
                else:
                    data['text'] = 'Failed to write on disk {}'.format(self.data["path"])
                send_alert(self.api.services.find(template_uid='github.com/threefoldtech/0-templates/alerta/0.0.1'), data)

        else:
            if self._monitor_disk():
                self.state.set('status', 'running', 'ok')
            else:
                self.state.delete('status', 'running')
                data['text'] = 'Failed to write on disk {}'.format(self.data["path"])
                send_alert(self.api.services.find(template_uid='github.com/threefoldtech/0-templates/alerta/0.0.1'), data)
            
    def install(self):
        self.logger.info('Installing zerodb %s' % self.name)

        # generate admin password
        if not self.data['admin']:
            self.data['admin'] = j.data.idgenerator.generateXCharID(25)

        if not self.data['path']:
            node = self.api.services.get(template_account='threefoldtech', template_name='node')
            kwargs = {
                'disktype': self.data['diskType'],
                'size': self.data['size'],
                'name': self.name,
            }
            self.data['path'] = node.schedule_action('zdb_path', kwargs).wait(die=True).result
            if not self.data['path']:
                raise RuntimeError('Failed to find a suitable disk for the zerodb')

        self._reserve_port()
        self._deploy()
        self.state.set('actions', 'install', 'ok')
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def start(self):
        """
        start zerodb server
        """
        self.logger.info('Starting zerodb %s' % self.name)
        self.state.check('actions', 'install', 'ok')
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
        info = self._zerodb_sal.info
        try:
            self.state.check('status', 'running', 'ok')
            info['running'] = True
        except StateCheckError:
            info['running'] = False
        return info

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

        namespace = {'name': name, 'size': size, 'password': password, 'public': public}
        self.data['namespaces'].append(namespace)

        try:
            self._zerodb_sal.deploy()
        except:
            self.data['namespaces'].remove(namespace)
            self._zerodb_sal.deploy()
            raise

    def namespace_set(self, name, prop, value):
        """
        Set a property of a namespace
        :param name: namespace name
        :param prop: property name
        :param value: property value
        """
        self.state.check('status', 'running', 'ok')

        namespace = self._namespace_exists_update_delete(name, prop, value)
        if not namespace:
            raise LookupError('Namespace {} doesn\'t exist'.format(name))

        try:
            self._zerodb_sal.deploy()
        except:
            self._namespace_exists_update_delete(name, prop, namespace[prop])
            self._zerodb_sal.deploy()
            raise

    def namespace_delete(self, name):
        """
        Delete a namespace
        """
        self.state.check('status', 'running', 'ok')
        namespace = self._namespace_exists_update_delete(name, delete=True)
        if not namespace:
            return

        try:
            self._zerodb_sal.deploy()
        except:
            self.data['namespaces'].append(namespace)
            self._zerodb_sal.deploy()
            raise

    def connection_info(self):
        zdb_sal = self._zerodb_sal
        return {
            'ip': zdb_sal.node.public_addr,
            'storage_ip': zdb_sal.node.storage_addr,
            'port': self.data['nodePort'],
        }

    def _namespace_exists_update_delete(self, name, prop=None, value=None, delete=False):
        """
        Helper function to check if namespace <name> exists in self.data['namespaces'], and either update property <prop> with
        a new value or delete the namespace.
        It returns the namespace before any updates which is used in recovery in case the deploy on the zerodb fails.
        :param name: namespace name
        :param prop: property name
        :param value: property value
        :param delete: boolen indicating if the namespace should be deleted
        """
        if prop and delete:
            raise ValueError('Can\'t set property and delete at the same time')
        if prop and prop not in ['size', 'password', 'public']:
            raise ValueError('Property must be size, password, or public')

        for namespace in self.data['namespaces']:
            if namespace['name'] == name:
                ns = dict(namespace)
                if prop:
                    namespace[prop] = value
                if delete:
                    self.data['namespaces'].remove(namespace)
                return ns
        return False

    @retry(exceptions=ServiceNotFoundError, tries=3, delay=3, backoff=2)
    def _reserve_port(self):
        port_mgr = self.api.services.get(template_uid=PORT_MANAGER_TEMPLATE_UID, name='_port_manager')
        self.data['nodePort'] = port_mgr.schedule_action("reserve", {"service_guid": self.guid, 'n': 1}).wait(die=True).result[0]


def send_alert(alertas, alert):
    for alerta in alertas:
        alerta.schedule_action('send_alert', args={'data': alert})
