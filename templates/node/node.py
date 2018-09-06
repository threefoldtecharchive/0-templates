
from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry, timeout
from zerorobot.template.state import StateCheckError
import netaddr

CONTAINER_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/container/0.0.1'
VM_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/vm/0.0.1'
BOOTSTRAP_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/zeroos_bootstrap/0.0.1'
ZDB_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/zerodb/0.0.1'
CAPACITY_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/node_capacity/0.0.1'
NETWORK_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/network/0.0.1'
BRIDGE_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/bridge/0.0.1'
NODE_CLIENT = 'local'


class NoNamespaceAvailability(Exception):
    pass


class Node(TemplateBase):

    version = '0.0.1'
    template_name = 'node'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.recurring_action('_monitor', 30)  # every 30 seconds
        self.recurring_action('_network_monitor', 30)  # every 30 seconds
        self.recurring_action('_register', 10 * 60)  # every 10 minutes

    def validate(self):
        self.state.delete('disks', 'mounted')

        network = self.data.get('network')
        if network:
            self._validate_network(network)

    def _validate_network(self, network):
        cidr = network.get('cidr')
        if cidr:
            netaddr.IPNetwork(cidr)
        vlan = network.get('vlan')
        if not isinstance(vlan, int):
            raise ValueError('Network should have vlan configured')

    @property
    def _node_sal(self):
        """
        connection to the node
        """
        return j.clients.zos.get(NODE_CLIENT)

    def _monitor(self):
        self.logger.info('Monitoring node %s' % self.name)
        self.state.check('actions', 'install', 'ok')
        self._rename_cache()

        # make sure cache is always mounted
        sp = self._node_sal.storagepools.get('zos-cache')
        if not sp.mountpoint:
            self._node_sal.ensure_persistance()

        # check for reboot
        if self._node_sal.uptime() < self.data['uptime']:
            self.install()

        self.data['uptime'] = self._node_sal.uptime()

        try:
            self._node_sal.zerodbs.partition_and_mount_disks()
            self.state.set('disks', 'mounted', 'ok')
        except:
            self.state.delete('disks', 'mounted')

        try:
            # check if the node was rebooting and start containers and vms
            self.state.check('status', 'rebooting', 'ok')
            self._start_all_containers()
            self._start_all_vms()
            self.state.delete('status', 'rebooting')
        except StateCheckError:
            pass

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
        self.state.check('actions', 'install', 'ok')
        services = self.api.services.find(template_uid=CAPACITY_TEMPLATE_UID)
        if not services:
            self.api.services.create(template_uid=CAPACITY_TEMPLATE_UID,
                                     service_name='_node_capacity',
                                     data={},
                                     public=True)

    def _rename_cache(self):
        """Rename old cache storage pool to new convention if needed"""
        try:
            self.state.check("migration", "fs_cache_renamed", "ok")
            return
        except StateCheckError:
            pass

        poolname = '{}_fscache'.format(self._node_sal.name)
        try:
            sp = self._node_sal.storagepools.get(poolname)
        except ValueError:
            return

        if sp.mountpoint:
            self.logger.info("rename mounted volume %s..." % poolname)
            cmd = 'btrfs filesystem label %s sp_zos-cache' % sp.mountpoint
        else:
            self.logger.info("rename unmounted volume %s..." % poolname)
            cmd = 'btrfs filesystem label %s sp_zos-cache' % sp.devices[0]
        result = self._node_sal.client.system(cmd).get()
        if result.state == "SUCCESS":
            self.logger.info("Rebooting %s ..." % self._node_sal.name)
            self.state.set("migration", "fs_cache_renamed", "ok")
            self.reboot()
            raise RuntimeWarning("Aborting monitor because system is rebooting for a migration.")
        self.logger.error('error: %s' % result.stderr)

    @retry(Exception, tries=2, delay=2)
    def install(self):
        self.logger.info('Installing node %s' % self.name)
        self.data['version'] = '{branch}:{revision}'.format(**self._node_sal.client.info.version())

        # Set host name
        self._node_sal.client.system('hostname %s' % self.data['hostname']).get()
        self._node_sal.client.bash('echo %s > /etc/hostname' % self.data['hostname']).get()

        self.data['uptime'] = self._node_sal.uptime()
        self.state.set('actions', 'install', 'ok')

    def zdb_path(self, disktype, size, name, zdbinfo=None):
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
        if disktype == 'hdd':
            disktypes = ['HDD', 'ARCHIVE']
            tasks = []
            potentials = {info['mountpoint']: info['disk'] for info in self._node_sal.zerodbs.partition_and_mount_disks()}
            if not zdbinfo:
                zdbs = self.api.services.find(template_uid=ZDB_TEMPLATE_UID)
                for zdb in zdbs:
                    if zdb.name != name:
                        tasks.append(zdb.schedule_action('info'))
                results = self._wait_all(tasks, timeout=120, die=True)
                zdbinfo = sorted(list(zip(zdbs, results)), key=lambda x: x[1]['free'],  reverse=True)
            for zdb, info in zdbinfo:
                if info['path'] in potentials:
                    potentials.pop(info['path'])

            disks = [(self._node_sal.disks.get(diskname), mountpoint) for mountpoint, diskname in potentials.items()]
            disks = list(filter(lambda disk: (disk[0].size / 1024 ** 3) > size and disk[0].type.value in disktypes, disks))
            disks.sort(key=lambda disk: disk[0].size, reverse=True)
            if not disks:
                return '', ''
            return disks[0][1], disks[0][0].name
        else:
            disktypes = ['SSD', 'NVME']
            return self._node_sal.zerodbs.create_and_mount_subvolume(name, size, disktypes)

    def _create_zdb(self, diskname, mountpoint, mode, zdb_size, disktype, namespaces):
        """Create a zerodb service

        :param diskname: disk or subvolume name
        :type diskname: string
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

        zdb_name = 'zdb_%s_%s' % (self.name, diskname)
        zdb_data = {
            'path': mountpoint,
            'mode': mode,
            'sync': False,
            'diskType': disktype,
            'size': zdb_size,
            'namespaces': namespaces
        }

        zdb = self.api.services.find_or_create(ZDB_TEMPLATE_UID, zdb_name, zdb_data)
        zdb.schedule_action('install').wait(die=True)
        zdb.schedule_action('start').wait(die=True)
        return zdb_name

    def create_zdb_namespace(self, disktype, mode, password, public, ns_size, name='', zdb_size=None):
        if disktype not in ['hdd', 'ssd']:
            raise ValueError('Disktype should be hdd or ssd')
        if mode not in ['seq', 'user', 'direct']:
            raise ValueError('ZDB mode should be user, direct or seq')

        if disktype == 'hdd':
            disktypes = ['HDD', 'ARCHIVE']
        else:
            disktypes = ['SSD', 'NVME']

        namespace_name = j.data.idgenerator.generateXCharID(10) if not name else name
        zdb_name = j.data.idgenerator.generateXCharID(5)

        zdb_size = zdb_size if zdb_size else ns_size
        tasks = []
        zdbs = self.api.services.find(template_uid=ZDB_TEMPLATE_UID)
        for zdb in zdbs:
            tasks.append(zdb.schedule_action('info'))
        results = self._wait_all(tasks, timeout=120, die=True)
        zdbinfo = sorted(list(zip(zdbs, results)), key=lambda x: x[1]['free'],  reverse=True)
        namespace = {
            'name': namespace_name,
            'size': ns_size,
            'password': password,
            'public': public,
        }
        mountpoint, name = self.zdb_path(disktype, zdb_size, zdb_name, zdbinfo)
        if mountpoint:
            return self._create_zdb(name, mountpoint, mode, zdb_size, disktype, [namespace]), namespace_name

        zdbinfo = list(filter(lambda info: info[1]['mode'] == mode and (info[1]['free'] / 1024 ** 3) > zdb_size and info[1]['type'] in disktypes, zdbinfo))
        if not zdbinfo:
            message = 'Not enough free space for namespace creation with size {} and type {}'.format(ns_size, ','.join(disktypes))
            raise NoNamespaceAvailability(message)

        for bestzdb, _ in zdbinfo:
            namespaces = [ns['name'] for ns in bestzdb.schedule_action('namespace_list').wait(die=True).result]
            if namespace_name not in namespaces:
                bestzdb.schedule_action('namespace_create', namespace).wait(die=True)
                return bestzdb.name, namespace_name

        message = 'Namespace {} already exists on all zerodbs'.format(namespace_name)
        raise NoNamespaceAvailability(message)

    def reboot(self):
        self._stop_all_containers()
        self._stop_all_vms()

        self.logger.info('Rebooting node %s' % self.name)
        self.state.set('status', 'rebooting', 'ok')
        self._node_sal.reboot()

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

    def _start_all_containers(self):
        for container in self.api.services.find(template_uid=CONTAINER_TEMPLATE_UID):
            container.schedule_action('start')

    def _start_all_vms(self):
        # TODO
        pass

    def _stop_all_containers(self):
        tasks = []
        for container in self.api.services.find(template_uid=CONTAINER_TEMPLATE_UID):
            tasks.append(container.schedule_action('stop'))
        self._wait_all(tasks)

    def _stop_all_vms(self):
        # TODO
        pass

    def _wait_all(self, tasks, timeout=60, die=False):
        results = []
        for t in tasks:
            results.append(t.wait(timeout=timeout, die=die).result)
        return results
