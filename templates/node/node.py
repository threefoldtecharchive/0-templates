
from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry, timeout
from zerorobot.template.state import StateCheckError
import netaddr
import time

CONTAINER_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/container/0.0.1'
VM_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/vm/0.0.1'
BOOTSTRAP_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/zeroos_bootstrap/0.0.1'
ZDB_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/zerodb/0.0.1'
CAPACITY_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/node_capacity/0.0.1'
NETWORK_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/network/0.0.1'
PORT_MANAGER_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/node_port_manager/0.0.1'
BRIDGE_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/bridge/0.0.1'
NODE_CLIENT = 'local'

GiB = 1024 ** 3


class NoNamespaceAvailability(Exception):
    pass


class Node(TemplateBase):

    version = '0.0.1'
    template_name = 'node'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self._node_sal = j.clients.zos.get(NODE_CLIENT)
        self.recurring_action('_monitor', 30)  # every 30 seconds
        self.recurring_action('_network_monitor', 30)  # every 30 seconds
        self.gl_mgr.add("_register", self._register)
        self.gl_mgr.add("_port_manager", self._port_manager)

    def validate(self):
        service = self.api.services.find(template_name='node')
        if service:
            raise Exception("The node service already exist (should one per node)")
        self.state.delete('disks', 'mounted')

        network = self.data.get('network')
        if network:
            _validate_network(network)

    def _monitor(self):
        self.logger.info('Monitoring node %s' % self.name)
        self.state.check('actions', 'install', 'ok')

        # make sure cache is always mounted
        sp = self._node_sal.storagepools.get('zos-cache')
        if not sp.mountpoint:
            self._node_sal.ensure_persistance()

        # check for reboot
        if self._node_sal.uptime() < self.data['uptime']:
            self.install()

        self.data['uptime'] = self._node_sal.uptime()

        try:
            self._node_sal.zerodbs.prepare()
            self.state.set('disks', 'mounted', 'ok')
        except:
            self.state.delete('disks', 'mounted')

    def _network_monitor(self):
        self.state.check('actions', 'install', 'ok')

        # make sure the bridges are installed
        for service in self.api.services.find(template_uid=BRIDGE_TEMPLATE_UID):
            self.logger.info("configuring bridge %s" % service.name)
            service.schedule_action('install').wait(die=True)

        # make sure the networks are configured
        for service in self.api.services.find(template_uid=NETWORK_TEMPLATE_UID):
            self.logger.info("configuring network %s" % service.name)
            service.schedule_action('configure').wait(die=True)

    def _register(self):
        """
        make sure the node_capacity service is installed
        """
        while True:
            try:
                self.state.check('actions', 'install', 'ok')
                self.api.services.find_or_create(template_uid=CAPACITY_TEMPLATE_UID,
                                                 service_name='_node_capacity',
                                                 data={},
                                                 public=True)
                return
            except StateCheckError:
                time.sleep(5)

    def _port_manager(self):
        """
        make sure the node_port_manager service is installed
        """
        while True:
            try:
                self.state.check('actions', 'install', 'ok')
                self.api.services.find_or_create(template_uid=PORT_MANAGER_TEMPLATE_UID,
                                                 service_name='_port_manager',
                                                 data={})
                return
            except StateCheckError:
                time.sleep(5)

    @retry(Exception, tries=2, delay=2)
    def install(self):
        self.logger.info('Installing node %s' % self.name)
        self.data['version'] = '{branch}:{revision}'.format(**self._node_sal.client.info.version())

        # Set host name
        self._node_sal.client.system('hostname %s' % self.data['hostname']).get()
        self._node_sal.client.bash('echo %s > /etc/hostname' % self.data['hostname']).get()

        self.data['uptime'] = self._node_sal.uptime()
        self.state.set('actions', 'install', 'ok')

    def reboot(self):
        self.logger.info('Rebooting node %s' % self.name)
        self._node_sal.reboot()

    def zdb_path(self, disktype, size, name):
        """Create zdb mounpoint and subvolume

        :param disktype: type of the disk the zerodb will be deployed on
        :type disktype: string
        :param size: size of the zerodb
        :type size: int
        :param name: zerodb name
        :type name: string
        :param zdbinfo: list of zerodb services and their info
        :param zdbinfo: [(service, dict)], optional
        :return: zerodb mountpoint, subvolume name
        :rtype: (string, string)
        """
        node_sal = self._node_sal

        disks_types_map = {
            'hdd': ['HDD', 'ARCHIVE'],
            'ssd': ['SSD', 'NVME'],
        }

        # get all usable filesystem path for this type of disk and amount of storage
        def usable_storagepool(sp):
            if sp.type.value not in disks_types_map[disktype]:
                return False
            if (sp.size - sp.total_quota() / GiB) <= size:
                return False
            return True

        # all storage pool path of type disktypes and with more then size storage available
        storagepools = list(filter(usable_storagepool, node_sal.storagepools.list()))
        if not storagepools:
            raise ZDBPathNotFound("all storagepools are already used by a zerodb")

        if disktype == 'hdd':
            # sort less used pool first
            storagepools.sort(key=lambda sp: sp.size - sp.total_quota(), reverse=True)
            fs_paths = []
            for sp in storagepools:
                try:
                    fs = sp.get('zdb')
                    fs_paths.append(fs.path)
                except ValueError:
                    pass  # no zdb filesystem on this storagepool

            # all path used by installed zerodb services
            zdb_infos = self._list_zdbs_info()
            zdb_infos = filter(lambda info: info['service_name'] != name, zdb_infos)
            # sort result by free size, first item of the list is the the one with bigger free size
            results = sorted(zdb_infos, key=lambda r: r['free'], reverse=True)
            zdb_paths = [res['path'] for res in results]

            # path that are not used by zerodb services but have a storagepool, so we can use them
            free_path = list(set(fs_paths) - set(zdb_paths))
            if len(free_path) <= 0:
                raise ZDBPathNotFound("all storagepools are already used by a zerodb")
            return free_path[0]

        if disktype == 'ssd':
            # all storage pool path of type disktypes and with more then size storage available
            storagepools = list(filter(usable_storagepool, node_sal.storagepools.list()))
            if not storagepools:
                raise ZDBPathNotFound("Could not find any usable  storage pool. Not enough space for disk type %s" % disktype)

            fs = storagepools[0].create('zdb_{}'.format(name), size * GiB)
            return fs.path

        raise RuntimeError("unsupported disktype:%s" % disktype)

    def create_zdb_namespace(self, disktype, mode, password, public, ns_size, name='', zdb_size=None):
        if disktype not in ['hdd', 'ssd']:
            raise ValueError('Disktype should be hdd or ssd')
        if mode not in ['seq', 'user', 'direct']:
            raise ValueError('ZDB mode should be user, direct or seq')

        if disktype == 'hdd':
            disktypes = ['HDD', 'ARCHIVE']
        elif disktype == 'ssd':
            disktypes = ['SSD', 'NVME']
        else:
            raise ValueError("disk type %s not supported" % disktype)

        namespace_name = j.data.idgenerator.generateGUID() if not name else name
        zdb_name = j.data.idgenerator.generateGUID()

        zdb_size = zdb_size if zdb_size else ns_size
        namespace = {
            'name': namespace_name,
            'size': ns_size,
            'password': password,
            'public': public,
        }
        try:
            mountpoint = self.zdb_path(disktype, zdb_size, zdb_name)
            self._create_zdb(zdb_name, mountpoint, mode, zdb_size, disktype, [namespace])
            return zdb_name, namespace_name
        except ZDBPathNotFound:
            # at this point we could find a place where to create a new zerodb
            # let's look at the already existing one
            pass

        def usable_zdb(info):
            if info['mode'] != mode:
                return False
            if info['free'] / GiB < zdb_size:
                return False
            if info['type'] not in disktypes:
                return False
            if not info['running']:
                return False
            return True

        zdbinfos = list(filter(usable_zdb, self._list_zdbs_info()))
        if len(zdbinfos) <= 0:
            message = 'Not enough free space for namespace creation with size {} and type {}'.format(ns_size, ','.join(disktypes))
            raise NoNamespaceAvailability(message)

        # sort result by free size, first item of the list is the the one with bigger free size
        for zdbinfo in sorted(zdbinfos, key=lambda r: r['free'], reverse=True):
            zdb = self.api.services.get(template_uid=ZDB_TEMPLATE_UID, name=zdbinfo['service_name'])
            namespaces = [ns['name'] for ns in zdb.schedule_action('namespace_list').wait(die=True).result]
            if namespace_name not in namespaces:
                zdb.schedule_action('namespace_create', namespace).wait(die=True)
                return zdb.name, namespace_name
        message = 'Namespace {} already exists on all zerodbs'.format(namespace_name)
        raise NoNamespaceAvailability(message)

    @timeout(30, error_message='info action timeout')
    def info(self):
        return self._node_sal.client.info.os()

    @timeout(30, error_message='stats action timeout')
    def stats(self):
        return self._node_sal.client.aggregator.query()

    @timeout(30, error_message='processes action timeout')
    def processes(self):
        return self._node_sal.client.process.list()

    @timeout(30, error_message='os_version action timeout')
    def os_version(self):
        return self._node_sal.client.ping()[13:].strip()

    def _create_zdb(self, name, mountpoint, mode, zdb_size, disktype, namespaces):
        """Create a zerodb service

        :param name: zdb name
        :type name: string
        :param mountpoint: zerodb mountpoint
        :type mountpoint: string
        :param mode: zerodb mode
        :type mode: string
        :param zdb_size: size of the zerodb
        :type zdb_size: int
        :param disktype: type of the disk to deploy the zerodb on
        :type disktype: string
        :param namespaces: list of namespaces to create on the zerodb
        :type namespaces: [dict]
        :return: zerodb service name
        :rtype: string
        """
        zdb_data = {
            'path': mountpoint,
            'mode': mode,
            'sync': False,
            'diskType': disktype,
            'size': zdb_size,
            'namespaces': namespaces
        }

        zdb = self.api.services.find_or_create(ZDB_TEMPLATE_UID, name, zdb_data)
        zdb.schedule_action('install').wait(die=True)
        zdb.schedule_action('start').wait(die=True)

    def _list_zdbs_info(self):
        """
        list the paths used by all the zerodbs installed on the node

        :param excepted: list of zerodb service name that should be skipped
        :type excepted: [str]

        :return: a list of zerodb path sorted by free size descending
        :rtype: [str]
        """
        zdbs = self.api.services.find(template_uid=ZDB_TEMPLATE_UID)
        tasks = [zdb.schedule_action('info') for zdb in zdbs]
        results = []
        for t in tasks:
            result = t.wait(timeout=120, die=True).result
            result['service_name'] = t.service.name
            results.append(result)
        return results


def _validate_network(network):
    cidr = network.get('cidr')
    if cidr:
        netaddr.IPNetwork(cidr)
    vlan = network.get('vlan')
    if not isinstance(vlan, int):
        raise ValueError('Network should have vlan configured')


class ZDBPathNotFound(Exception):
    pass
