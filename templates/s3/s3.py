import math
import time
from itertools import zip_longest

import gevent
from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import timeout
from zerorobot.template.state import (SERVICE_STATE_ERROR, SERVICE_STATE_OK,
                                      SERVICE_STATE_SKIPPED,
                                      SERVICE_STATE_WARNING,
                                      StateCategoryNotExistsError,
                                      StateCheckError)

GATEWAY_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/gateway/0.0.1'
MINIO_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/minio/0.0.1'
NS_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/namespace/0.0.1'
ALERTA_UID = 'github.com/threefoldtech/0-templates/alerta/0.0.1'


class S3(TemplateBase):
    version = '0.0.1'
    template_name = "s3"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.__minio = None
        self.recurring_action('_monitor', 60)
        # self.recurring_action('_ensure_namespaces_connections', 300)
        self.recurring_action('_remove_deletable_namespaces', 86400)  # run once a day

        self._farm = j.sal_zos.farm.get(self.data['farmerIyoOrg'])

        self._robots = {}

    def validate(self):
        if self.data['parityShards'] > self.data['dataShards']:
            raise ValueError('parityShards must be equal to or less than dataShards')

        if len(self.data['minioPassword']) < 8:
            raise ValueError("minio password need to be at least 8 characters")

        for key in ['minioLogin', 'nsName', 'storageSize']:
            if not self.data[key]:
                raise ValueError('Invalid value for {}'.format(key))

        if not self.data['nsPassword']:
            self.data['nsPassword'] = j.data.idgenerator.generateXCharID(32)

        if self.data['tlog'] is None:
            self.data['tlog'] = {}
        if self.data['master'] is None:
            self.data['master'] = {}

    @property
    def _tlog_namespace(self):
        return '{}_tlog'.format(self.data['nsName'])

    @property
    def _nodes(self):
        nodes = self._farm.filter_online_nodes()
        if not nodes:
            raise ValueError('There are no online nodes in this farm')
        return nodes

    @property
    def _minio(self):
        if self.__minio is None:
            if self.data['minioLocation']['nodeId'] and self.data['minioLocation']['robotURL']:
                try:
                    robot = self.api.robots.get(
                        self.data['minioLocation']['nodeId'],
                        self.data['minioLocation']['robotURL'])
                    self.__minio = robot.services.get(template_uid=MINIO_TEMPLATE_UID, name=self.guid)
                except ConnectionError:
                    self.state.set('status', 'running', 'error')
        return self.__minio

    def _ensure_namespaces_connections(self):
        try:
            self.state.check('actions', 'install', 'ok')
        except StateCheckError:
            return

        self.logger.info("verify data backend namespace connections")

        def update_namespace(namespace):
            try:
                robot = self.api.robots.get(namespace['node'], namespace['url'])
                ns = robot.services.get(template_uid=NS_TEMPLATE_UID, name=namespace['name'])
                address = namespace_connection_info(ns)
                namespace['address'] = address
            except Exception as e:
                self.logger.error('can not get namespace %s address: %s, assume error.', namespace['name'], e)
                self.state.set('data_shards', namespace['address'], 'error')

        namespaces = self.data['namespaces']

        group = gevent.pool.Group()
        group.map(update_namespace, namespaces)
        group.join()

        namespaces_connection = sorted(map(lambda ns: ns['address'], namespaces))
        if not self.data.get('current_namespaces_connections'):
            self.data['current_namespaces_connections'] = sorted(namespaces_connection)

        if namespaces_connection == sorted(self.data['current_namespaces_connections']):
            self.logger.info("namespace connection in service data are in sync with reality")
        else:
            self.logger.info("some namespace connection in service data are not correct, updating minio configuration")
            # calling update_zerodbs will also tell minio process to reload its config
            self._minio.schedule_action('update_zerodbs', args={'zerodbs': namespaces_connection}).wait(die=True)
            self.data['current_namespaces_connections'] = namespaces_connection

        self.logger.info("verify tlog namespace connections")
        tlog = self.data.get('tlog', {})
        if tlog.get('node') and tlog.get('url'):
            robot = self.api.robots.get(self.data['tlog']['node'], self.data['tlog']['url'])

            try:
                namespace = robot.services.get(template_uid=NS_TEMPLATE_UID, name=self.data['tlog']['name'])
                connection_info = namespace_connection_info(namespace)
                if tlog.get('address') and tlog['address'] != connection_info:
                    self.logger.info(
                        "tlog namespace connection in service data is not correct, updating minio configuration")
                    t = self._minio.schedule_action('update_tlog', args={'namespace': self._tlog_namespace,
                                                                         'address': connection_info})
                    t.wait(die=True)
                    self.data['tlog']['address'] = connection_info
                else:
                    self.logger.info("tlog namespace connection in service data is in sync with reality")
            except Exception as e:
                self.logger.error("checking tlog namespace failed with error: %s. assume tlog down", e)
                self.state.set('tlog_shards', tlog['address'], 'error')

        self.logger.info("verify master namespace connections")
        master = self.data.get('master', {})
        if master.get('node') and master.get('url'):
            robot = self.api.robots.get(master['node'], master['url'])
            namespace = robot.services.get(template_uid=NS_TEMPLATE_UID, name=master['name'])

            try:
                connection_info = namespace_connection_info(namespace)
                if master.get('address') and master != connection_info:
                    self.logger.info(
                        "master namespace connection in service data is not correct, updating minio configuration")
                    t = self._minio.schedule_action('update_master', args={'namespace': self._tlog_namespace,
                                                                           'address': connection_info})
                    t.wait(die=True)
                    self.data['master']['address'] = connection_info
                else:
                    self.logger.info("master namespace connection in service data is in sync with reality")
            except Exception as e:
                self.logger.error("checking master tlog namespace failed with error: %s.", e)
                # nothing to do, it's responsibility of the active to report and fix this

    def _monitor(self):
        try:
            self.state.check('actions', 'install', 'ok')
        except StateCheckError:
            return
        self.logger.info('Monitor s3 %s' % self.name)

        self._bubble_minio_state()

        @timeout(10)
        def update_state():
            try:
                self._minio.state.check('status', 'running', 'ok')
                self.state.set('status', 'running', 'ok')
                return
            except StateCheckError:
                self.state.set('status', 'running', 'error')
                zdbs_connection = []
                for namespace in self.data['namespaces']:
                    robot = self.api.robots.get(namespace['node'], namespace['url'])
                    ns = robot.services.get(template_uid=NS_TEMPLATE_UID, name=namespace['name'])
                    try:
                        ns.state.check('status', 'running', 'ok')
                        zdbs_connection.append(namespace_connection_info(ns))
                    except StateCheckError:
                        break
                else:
                    self._minio.schedule_action('update_zerodbs', args={'zerodbs': zdbs_connection}).wait(die=True)

        try:
            update_state()
        except:
            self.state.set('status', 'running', 'error')

    def install(self):
        nodes = list(self._nodes)

        def get_master_info():
            robot = self.api.robots.get(self.data['master']['node'], self.data['master']['url'])
            namespace = robot.services.get(template_uid=NS_TEMPLATE_UID, name=self.data['master']['name'])
            master_connection = namespace_connection_info(namespace)
            self.data['master']['address'] = master_connection

            return {
                'address': master_connection,
                'namespace': self._tlog_namespace,
            }

        def deploy_data_namespaces(nodes):
            self._deploy_minio_backend_namespaces(nodes)
            self.logger.info("data backend namespaces deployed")

        def deploy_tlog_namespace(nodes):
            # prevent installing the tlog namespace on the same node as the minio
            to_exclude = [*self.data['excludeNodes']]
            if 'master' in self.data and 'node' in self.data['master']:
                if self.data['master']['node']:
                    to_exclude.append(self.data['master']['node'])

            if len(nodes) - len(to_exclude) > 1:
                nodes = list(filter(lambda n: n['node_id'] not in to_exclude, nodes))

            self._deploy_minio_tlog_namespace(nodes)
            self.logger.info("tlog backend namespaces deployed")

        # deploy all namespaces
        ns_data_gl = gevent.spawn(deploy_data_namespaces, nodes)
        tasks = [ns_data_gl]

        master = {'namespace': '', 'address': ''}
        if self.data['master'].get('name'):
            master_gl = gevent.spawn(get_master_info)
            tasks.append(master_gl)

        self.logger.info("wait for data namespaces to be installed")
        gevent.wait(tasks)

        if ns_data_gl.exception:
            raise ns_data_gl.exception
        self.data['current_namespaces_connections'] = sorted([ns['address'] for ns in self.data['namespaces']])

        ns_tlog_gl = gevent.spawn(deploy_tlog_namespace, nodes)
        ns_tlog_gl.join()
        if ns_tlog_gl.exception:
            raise ns_tlog_gl.exception

        if self.data['master'].get('name'):
            if master_gl.exception:
                raise master_gl.exception

        # exlude node where the minio cannot be installed
        to_exclude = [*self.data['excludeNodes']]
        if 'tlog' in self.data and 'node' in self.data['tlog']:
            if self.data['tlog']['node']:
                to_exclude.append(self.data['tlog']['node'])

        if 'master' in self.data and 'node' in self.data['master']:
            if self.data['master']['node']:
                to_exclude.append(self.data['master']['node'])

        if to_exclude and len(nodes) - len(to_exclude) > 1:
            nodes = list(filter(lambda n: n['node_id'] not in to_exclude, nodes))

        self._deploy_minio(nodes)
        self.state.set('actions', 'install', 'ok')
        self.state.set('status', 'running', 'ok')

    def _delete_namespace(self, namespace):
        self.logger.info("deleting namespace %s on node %s", namespace['node'], namespace['url'])
        robot = self.api.robots.get(namespace['node'], namespace['url'])

        try:
            ns = robot.services.get(template_uid=NS_TEMPLATE_UID, name=namespace['name'])
            ns.delete()
        except ServiceNotFoundError:
            pass
        except Exception:
            if namespace not in self.data['deletableNamespaces']:
                self.data['deletableNamespaces'].append(namespace)

    def _remove_deletable_namespaces(self):
        namespaces = self.data['deletableNamespaces'].copy()
        for namespace in namespaces:
            self.logger.info("deleting namespace %s on node %s", namespace['node'], namespace['url'])
            robot = self.api.robots.get(namespace['node'], namespace['url'])
            try:
                ns = robot.services.get(template_uid=NS_TEMPLATE_UID, name=namespace['name'])
                ns.delete()
                self.data['deletableNamespaces'].remove(namespace)
            except ServiceNotFoundError:
                self.data['deletableNamespaces'].remove(namespace)
            except:
                pass

    def _update_namespaces(self, namespaces):
        """
        updates the namespaces then call install to make sure that the namespace is deployed
        """
        self.data['namespaces'] = namespaces
        self.state.delete('data_shards')
        self.install()

    def uninstall(self):
        self.logger.info("Uninstall s3 {}".format(self.name))
        try:
            # uninstall and delete minio service
            self.logger.info("deleting minio")
            if self._minio:
                self._minio.schedule_action('uninstall').wait(die=True)
                self._minio.delete()
                self.data['minioLocation']['nodeId'] = ''
                self.data['minioLocation']['robotURL'] = ''
                self.data['minioLocation']['public'] = ''
                self.data['minioLocation']['storage'] = ''
                self.__minio = None
        except ServiceNotFoundError:
            pass

        # delete all the created namespaces
        group = gevent.pool.Group()
        namespaces = list(self.data['namespaces'])
        if self.data['tlog'].get('node'):
            namespaces.append(self.data['tlog'])
        group.map(self._delete_namespace, namespaces)
        group.join()
        self.data['tlog'] = {}
        self.data['current_namespaces_connections'] = None

        self.state.delete('actions', 'install')
        self.state.delete('status', 'running')

    def url(self):
        self.state.check('actions', 'install', 'ok')
        return {
            'public': self.data['minioLocation']['public'],
            'storage': self.data['minioLocation']['storage'],
        }

    def start(self):
        self.state.check('actions', 'install', 'ok')
        self._minio.schedule_action('start').wait(die=True)

    def stop(self):
        self.state.check('actions', 'install', 'ok')
        self._minio.schedule_action('stop').wait(die=True)

    def upgrade(self):
        self.state.check('actions', 'install', 'ok')
        self._minio.schedule_action('upgrade').wait(die=True)

    def tlog(self):
        return self.data['tlog']

    def update_master(self, master):
        self.data['master'] = master

    def namespaces(self):
        return self.data['namespaces']

    def promote(self):
        """
        Promote s3 by clearing its master section and reloading minio
        """
        self.data['master'] = dict()
        self._minio.schedule_action('update_master', args={'namespace': '', 'address': ''}).wait(die=True)

    def redeploy(self, reset_tlog=True, exclude_nodes=None):
        """
        Redeploys the tlog and minio
        """
        self.state.check('actions', 'install', 'ok')

        # make sure we reset error stats
        self.state.delete('data_shards')
        self.state.delete('tlog_shards')
        self.state.delete('vm')

        try:
            if self._minio:
                self._minio.schedule_action('uninstall').wait(die=True)
        except ServiceNotFoundError:
            pass

        if reset_tlog and 'node' in self.data['tlog'] and 'url' in self.data['tlog']:
            self._delete_namespace(self.data['tlog'])
            self.data['tlog'] = {}

        if exclude_nodes:
            if not isinstance(exclude_nodes, list):
                exclude_nodes = [exclude_nodes]
            self.data['excludeNodes'] = exclude_nodes
        self.install()

    def _deploy_minio_backend_namespaces(self, nodes):
        self.logger.info("create namespaces to be used as a backend for minio")

        self.logger.info("compute how much zerodb are required")
        required_nr_namespaces, namespace_size = compute_minimum_namespaces(total_size=self.data['storageSize'],
                                                                            data=self.data['dataShards'],
                                                                            parity=self.data['parityShards'])
        deployed_namespaces = []

        # Check if namespaces have already been created in a previous install attempt
        if self.data['namespaces']:
            for namespace in self.data['namespaces']:
                robot = self.api.robots.get(namespace['node'], namespace['url'])
                try:
                    namespace = robot.services.get(template_uid=NS_TEMPLATE_UID, name=namespace['name'])
                    deployed_namespaces.append(namespace)
                except ServiceNotFoundError:
                    continue

        self.logger.info("namespaces required: %d of %dGB", required_nr_namespaces, namespace_size)
        self.logger.info("namespaces already deployed %d", len(deployed_namespaces))
        required_nr_namespaces = required_nr_namespaces - len(deployed_namespaces)
        for namespace, node in self._deploy_namespaces(nr_namepaces=required_nr_namespaces,
                                                       name=self.data['nsName'],
                                                       size=namespace_size,
                                                       storage_type=self.data['storageType'],
                                                       password=self.data['nsPassword'],
                                                       nodes=nodes):
            deployed_namespaces.append(namespace)
            address = namespace_connection_info(namespace)
            self.data['namespaces'].append({'name': namespace.name,
                                            'url': node['robot_address'],
                                            'node': node['node_id'],
                                            'address': address})
            self.state.set('data_shards', address, SERVICE_STATE_OK)

            deployed_nr_namespaces = len(deployed_namespaces)
            self.logger.info("%d namespaces deployed, remaining %s", deployed_nr_namespaces,
                             required_nr_namespaces - deployed_nr_namespaces)
            self.save()  # to save the already deployed namespaces

        if len(deployed_namespaces) < required_nr_namespaces:
            raise RuntimeError("could not deploy enough namespaces for minio data backend")

        return deployed_namespaces

    def _handle_data_shard_failure(self):
        """
        handling data shards failures
        1. list all the shards marqued as in error state
        2. walk over the list of failed shards
            2.1 for each failed shard that is in failure for more then 2 hours, mark as to replace
        3. walk over the list of shads to replace
        4. if more the parity shards needs to be replaced, mark as degrated and stop
        5.  replace the shards with new one
            5.1 update minio config with new shards
            5.2 call check_and_repair to copy data to new shards
            5.3 delete all shards that have been replaced
        """
        nodes = self._nodes
        N = self.data['parityShards']
        namespaces_by_addr = {ns['address']: ns for ns in self.data['namespaces']}

        # 1. list all the shards marqued as in error state
        failed_shards = [address for address, state in self.state.get('data_shards').items() if state == 'error']

        # 2. walk over the list of failed shards
        to_replace = []
        for addr in failed_shards:

            # 3.1 if more the parity shards needs to be replaced, mark as degrated
            namespace = namespaces_by_addr.get(addr)
            if not namespace:
                # this state reference a shards we're not using
                continue
             # if the error started more then 2 hours ago, then mark the shard to be replaced
            if 'error_started' in namespace and namespace['error_started'] < (int(time.time()) - 7200):
                to_replace.append(namespace)

        # 4. if more the parity shards needs to be replaced, mark as degrated and stop
        if len(to_replace) > N:
            error_msg = "Too many shard down (%d), cannot repair now. Need %s more shards up" % (
                to_replace, failed_shards-N)
            self.logger.error(error_msg)
            self._send_alert(
                ressource="Cannot repair data shards on %s" % self._minio.name,
                text=error_msg,
                tags=['minio_name:%s' % self._minio.name],
                event='healing')
            self.state.set('healing', 'blocked', 'ok')
            raise RuntimeError()

        self.state.delete('healing')

        if not to_replace:
            # nothing to do for now, just send the current shards address to minio
            # so minio can update its state
            new_shards = [ns['address'] for ns in self.data['namespaces']]
            self._minio.schedule_action('update_zerodbs', {'zerodbs': new_shards, 'reload': False})
            return

        # 5. replace the shards with new one
        for namespace in to_replace:
            self.state.delete('data_shards', namespace['address'])
            self.data['namespaces'].remove(namespace)

        # 5.1 deploy N new namespaces
        self._deploy_minio_backend_namespaces(nodes)

        # 5.2 update minio config with new shards
        new_shards = [ns['address'] for ns in self.data['namespaces']]
        self._minio.schedule_action('update_zerodbs', {'zerodbs': new_shards, 'reload': True}).wait(die=True)

        # 5.3 call check_and_repair to copy data to new shards
        self._minio.schedule_action('check_and_repair', {'block': True}).wait(die=True)

        for namespace in to_replace:
            gevent.spawn(self._delete_namespace(namespace))

        # if we return the namespaces, s3_redundant knows he needs to update the passive minio
        # with the new namespaces
        return self.data['namespaces']

    def _deploy_minio_tlog_namespace(self, nodes):
        self.logger.info("create namespaces to be used as a tlog for minio")

        namespace = None
        try:
            # Check if namespaces have already been created in a previous install attempt
            if self.data.get('tlog') and self.data['tlog']['node'] and self.data['tlog']['url']:
                robot = self.api.robots.get(self.data['tlog']['node'], self.data['tlog']['url'])
                namespace = robot.services.get(template_uid=NS_TEMPLATE_UID, name=self.data['tlog']['name'])
                namespace.schedule_action('install').wait(die=True)
                return namespace
        except Exception as e:
            self.logger.error("failed to reuse namespace %s: %s", namespace, e)

        tlog_namespace = None
        for namespace, node in self._deploy_namespaces(nr_namepaces=1,
                                                       name=self._tlog_namespace,
                                                       size=10,  # TODO: compute how much is needed
                                                       storage_type='ssd',
                                                       password=self.data['nsPassword'],
                                                       nodes=nodes):
            tlog_namespace = namespace
            address = namespace_connection_info(namespace)
            self.data['tlog'] = {'name': tlog_namespace.name,
                                 'url': node['robot_address'],
                                 'node': node['node_id'],
                                 'address': address}
            self.state.set('tlog_shards', address, SERVICE_STATE_OK)
        if not tlog_namespace:
            raise RuntimeError("could not deploy tlog namespace for minio")

        self.logger.info("tlog namespaces deployed")
        self.save()  # to save the already deployed namespaces

        return tlog_namespace

    def _deploy_namespaces(self, nr_namepaces, name,  size, storage_type, password, nodes):
        """
        generic function to deploy a group namespaces

        This function will yield namespaces as they are created
        It can return once nr_namespaces has been created or if we cannot create namespaces on any nodes.
        It is up to the caller to count the number of namespaces received from this function to know if the deployed enough namespaces
        """

        if storage_type not in ['ssd', 'hdd']:
            raise ValueError("storage_type must be 'ssd' or 'hdd', not %s" % storage_type)

        storage_key = 'sru' if storage_type == 'ssd' else 'hru'

        required_nr_namespaces = nr_namepaces
        deployed_nr_namespaces = 0
        while deployed_nr_namespaces < required_nr_namespaces:
            # sort nodes by the amount of storage available
            nodes = sort_by_less_used(nodes, storage_key)
            self.logger.info('number of possible nodes to use for namespace deployments %s', len(nodes))
            if len(nodes) <= 0:
                return

            gls = set()
            for i in range(required_nr_namespaces - deployed_nr_namespaces):
                node = nodes[i % len(nodes)]
                self.logger.info("try to install namespace %s on node %s", name, node['node_id'])
                gls.add(gevent.spawn(self._install_namespace,
                                     node=node,
                                     name=name,
                                     disk_type=storage_type,
                                     size=size,
                                     password=password))

            for g in gevent.iwait(gls):
                if g.exception and g.exception.node in nodes:
                    self.logger.error(
                        "we could not deploy on node %s, remove it from the possible node to use", node['node_id'])
                    nodes.remove(g.exception.node)
                else:
                    namespace, node = g.value
                    deployed_nr_namespaces += 1

                    # update amount of ressource so the next iteration of the loop will sort the list of nodes properly
                    nodes[nodes.index(node)]['used_resources'][storage_key] += size

                    yield (namespace, node)

    def _install_namespace(self, node, name, disk_type, size, password):
        robot = self.api.robots.get(node['node_id'], node['robot_address'])
        try:
            data = {
                'diskType': disk_type,
                'mode': 'direct',
                'password': password,
                'public': False,
                'size': size,
                'nsName': name,
            }
            namespace = robot.services.create(template_uid=NS_TEMPLATE_UID, data=data)
            task = namespace.schedule_action('install').wait(timeout=300)
            if task.eco:
                namespace.delete()
                raise NamespaceDeployError(task.eco.message, node)
            return namespace, node

        except Exception as err:
            raise NamespaceDeployError(str(err), node)

    def _bubble_minio_state(self):
        """
        copy namespaces state from minio service and bubble it up
        """
        try:
            self.state.check('actions', 'install', 'ok')
        except StateCheckError:
            return

        def do():
            self.logger.info("bubble up minio state")
            try:
                self.state.set('vm', 'disk', self._minio.state.get('vm', 'disk')['disk'])
            except StateCheckError:
                self.state.set('vm', 'disk', 'error')
                self.state.set('status', 'running', 'error')
                self._send_alert(
                    "tlog disk from minio_name:%s" % self._minio.name,
                    text="Minio Tlog disk is in error state",
                    tags=['minio_name:%s' % self._minio.name],
                    event='storage')
            except StateCategoryNotExistsError:
                # probably no state set on the minio disk #FIXME
                self.state.delete('vm')
            except ServiceNotFoundError:
                self.state.delete('data_shards')
                self.state.delete('tlog_shards')
                self.state.delte('vm')
                self.state.set('status', 'running', 'error')
                return

            namespaces_by_addr = {ns['address']: ns for ns in self.data['namespaces']}
            try:
                for addr, minio_shard_state in self._minio.state.get('data_shards').items():
                    if minio_shard_state == SERVICE_STATE_ERROR:
                        self._send_alert(
                            addr,
                            text='data shard %s is in error state' % addr,
                            tags=['shard:%s' % addr],
                            event='storage')

                    # when we detect a shards in failure. We keep the time the failure has been detected
                    # so during self-healin we can decide what to do base on the amount of
                    # time the shard has been down
                    try:
                        s3_shard_state = self.state.get('data_shards', addr)[addr]
                    except StateCategoryNotExistsError:
                        s3_shard_state = None

                    namespace = namespaces_by_addr.get(addr)
                    if not namespace:
                        continue

                    if s3_shard_state == SERVICE_STATE_OK and minio_shard_state == SERVICE_STATE_ERROR:
                        # switch from ok to error, we track the time
                        namespace['error_started'] = int(time.time())
                    elif s3_shard_state == SERVICE_STATE_ERROR and minio_shard_state == SERVICE_STATE_ERROR and 'error_started' not in namespace:
                        # no switch, but we should had an time, set it now
                        namespace['error_started'] = int(time.time())
                    # elif s3_shard_state == SERVICE_STATE_ERROR and minio_shard_state == SERVICE_STATE_OK:
                    #     # switch from error to ok
                    #     if 'error_started' in namespace:
                    #         del namespace['error_started']

                    self.state.set('data_shards', addr, minio_shard_state)

                for addr, minio_shard_state in self._minio.state.get('tlog_shards').items():
                    self.state.set('tlog_shards', addr, minio_shard_state)
                    if minio_shard_state == SERVICE_STATE_ERROR:
                        self._send_alert(
                            addr,
                            text='tlog shard %s is in error state' % addr,
                            tags=['shard:%s' % addr],
                            event='storage')
            except StateCategoryNotExistsError:
                pass

        try:
            do()
        except:
            self.state.set('status', 'running', 'error')

    def _deploy_minio(self, nodes):
        nodes = sort_minio_node_candidates(nodes)
        minio_robot = self.api.robots.get(nodes[0]['node_id'], nodes[0]['robot_address'])

        self.logger.info("create the minio service")
        minio_data = {
            'zerodbs': [ns['address'] for ns in self.data['namespaces']],
            'namespace': self.data['nsName'],
            'nsSecret': self.data['nsPassword'],
            'login': self.data['minioLogin'],
            'password': self.data['minioPassword'],
            'dataShard': self.data['dataShards'],
            'parityShard': self.data['parityShards'],
            'tlog': {
                'namespace': self._tlog_namespace,
                'address': self.data['tlog']['address'],
            },
            'master': {
                'address': self.data['master'].get('address') if 'master' in self.data else None,
                'namespace': self._tlog_namespace,
            },
            'blockSize': self.data['minioBlockSize'],
        }

        try:
            minio = minio_robot.services.get(template_uid=MINIO_TEMPLATE_UID, name=self.guid)
            minio.schedule_action('update_all', args={
                'zerodbs': minio_data['zerodbs'],
                'tlog': minio_data['tlog'],
                'master': minio_data['master'],
            }).wait(die=True)
        except ServiceNotFoundError:
            minio = minio_robot.services.create(MINIO_TEMPLATE_UID, self.guid, minio_data)

        if not minio:
            raise RuntimeError('Failed to create minio service')

        self.data['minioLocation']['nodeId'] = nodes[0]['node_id']
        self.data['minioLocation']['robotURL'] = nodes[0]['robot_address']
        self.save()

        self.logger.info("install minio")
        minio.schedule_action('install').wait(die=True)
        minio.schedule_action('start').wait(die=True)
        connection_info = minio.schedule_action('connection_info').wait(die=True).result
        self.data['minioLocation']['public'] = connection_info['public']
        self.data['minioLocation']['storage'] = connection_info['storage']
        self.logger.info("minio installed")

        self.__minio = minio

    def _send_alert(self, ressource, text, tags, event, severity='critical'):
        alert = {
            'attributes': {},
            'resource': ressource,
            'environment': 'Production',
            'severity': severity,
            'event': event,
            'tags': tags,
            'service': [self.name],
            'text': text,
        }
        for alerta in self.api.services.find(template_uid=ALERTA_UID):
            alerta.schedule_action('send_alert', args={'data': alert})


def compute_minimum_namespaces(total_size, data, parity):
    """
    compute the number and size of zerodb namespace required to
    fulfill the erasure coding policy

    :param total_size: total size of the s3 storage
    :type total_size: int
    :param data: data shards number
    :type data: int
    :param parity: parity shard number
    :type parity: int
    :return: tuple with (number,size) of zerodb namespace required
    :rtype: tuple
    """
    max_shard_size = 1000  # 1TB

    # compute the require size to be able to store all the data+parity
    required_size = math.ceil((total_size * (data+parity)) / data)

    # take the minimum nubmer of shard and add a 25% to it
    nr_shards = math.ceil((data+parity) * 1.25)

    # compute the size of the shards
    shard_size = math.ceil(required_size / (data+parity))
    # if shard size is bigger then max, we limite the shard size
    # and increase the number of shards
    if shard_size > max_shard_size:
        shard_size = max_shard_size
        nr_shards = math.ceil(required_size / shard_size)

    return nr_shards, shard_size


def namespaces_connection_info(namespaces):
    group = gevent.pool.Group()
    return list(group.imap_unordered(namespace_connection_info, namespaces))


def namespace_connection_info(namespace):
    result = namespace.schedule_action('connection_info').wait(die=True).result
    # if there is not special storage network configured,
    # then the sal return the zerotier as storage address
    return '{}:{}'.format(result['storage_ip'], result['port'])


def sort_by_less_used(nodes, storage_key):
    def key(node):
        return (-node['total_resources'][storage_key], node['used_resources'][storage_key])
    return sorted(nodes, key=key)


def sort_minio_node_candidates(nodes):
    """
    to select a candidate node for minio install
    we sort by
    - amount of cpu: the node with the most cpu but least used
    - amount of sru: the node with the most sru but least used
    """

    def key(node):
        return (-node['total_resources']['cru'],
                -node['total_resources']['sru'],
                node['used_resources']['cru'],
                node['used_resources']['sru'])
    return sorted(nodes, key=key)


def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


class NamespaceDeployError(RuntimeError):
    def __init__(self, msg, node):
        super().__init__(self, msg)
        self.node = node
