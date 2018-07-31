
from js9 import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry, timeout
from zerorobot.template.state import StateCheckError
import netaddr

CONTAINER_TEMPLATE_UID = 'github.com/zero-os/0-templates/container/0.0.1'
VM_TEMPLATE_UID = 'github.com/zero-os/0-templates/vm/0.0.1'
BOOTSTRAP_TEMPLATE_UID = 'github.com/zero-os/0-templates/zeroos_bootstrap/0.0.1'
ZDB_TEMPLATE_UID = 'github.com/zero-os/0-templates/zerodb/0.0.1'
NODE_CLIENT = 'local'


class Node(TemplateBase):

    version = '0.0.1'
    template_name = 'node'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.recurring_action('_monitor', 30)  # every 30 seconds
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
    def node_sal(self):
        """
        connection to the node
        """
        return j.clients.zos.sal.get_node(NODE_CLIENT)

    def _monitor(self):
        self.logger.info('Monitoring node %s' % self.name)
        self.state.check('actions', 'install', 'ok')
        self._rename_cache()

        # make sure cache is always mounted
        sp = self.node_sal.storagepools.get('zos-cache')
        if not sp.mountpoint:
            self.node_sal.ensure_persistance()

        # check for reboot
        if self.node_sal.uptime() < self.data['uptime']:
            self.install()

        self.data['uptime'] = self.node_sal.uptime()

        try:
            self.node_sal.zerodbs.partition_and_mount_disks()
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

    @retry(RuntimeError, tries=5, delay=5, backoff=2)
    def _register(self):
        """
        register the node capacity
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info("register node capacity")

        self.node_sal.capacity.register()
        self.node_sal.capacity.update_reality()
        self.node_sal.capacity.update_reserved(
            vms=self.api.services.find(template_name='vm', template_account='zero-os'),
            vdisks=self.api.services.find(template_name='vdisk', template_account='zero-os'),
            gateways=self.api.services.find(template_name='gateway', template_account='zero-os'),
        )

    def _rename_cache(self):
        """Rename old cache storage pool to new convention if needed"""
        try:
            self.state.check("migration", "fs_cache_renamed", "ok")
            return
        except StateCheckError:
            pass

        poolname = '{}_fscache'.format(self.node_sal.name)
        try:
            sp = self.node_sal.storagepools.get(poolname)
        except ValueError:
            self.logger.info("storage pool %s doesn't exist on node %s" % (poolname, self.node_sal.name))
            return

        if sp.mountpoint:
            self.logger.info("rename mounted volume %s..." % poolname)
            cmd = 'btrfs filesystem label %s sp_zos-cache' % sp.mountpoint
        else:
            self.logger.info("rename unmounted volume %s..." % poolname)
            cmd = 'btrfs filesystem label %s sp_zos-cache' % sp.devices[0]
        result = self.node_sal.client.system(cmd).get()
        if result.state == "SUCCESS":
            self.logger.info("Rebooting %s ..." % self.node_sal.name)
            self.state.set("migration", "fs_cache_renamed", "ok")
            self.reboot()
            raise RuntimeWarning("Aborting monitor because system is rebooting for a migration.")
        self.logger.error('error: %s' % result.stderr)

    def _configure_network(self):
        network = self.data.get('network')
        if network and network.get('cidr'):
            self.logger.info("install OpenVSwitch container")
            driver = network.get('driver')
            if driver:
                self.logger.info("reload driver {}".format(driver))
                self.node_sal.network.reload_driver(driver)

            self.logger.info("configure network: cidr: {cidr} - vlan tag: {vlan}".format(**network))
            self.node_sal.network.configure(
                cidr=network['cidr'],
                vlan_tag=network['vlan'],
                ovs_container_name='ovs',
                bonded=network.get('bonded', False),
            )

    @retry(Exception, tries=2, delay=2)
    def install(self):
        self.logger.info('Installing node %s' % self.name)
        self.data['version'] = '{branch}:{revision}'.format(**self.node_sal.client.info.version())

        # Set host name
        self.node_sal.client.system('hostname %s' % self.data['hostname']).get()
        self.node_sal.client.bash('echo %s > /etc/hostname' % self.data['hostname']).get()
        # Configure networkj
        self._configure_network()

        self.data['uptime'] = self.node_sal.uptime()
        self.state.set('actions', 'install', 'ok')

    def configure_network(self, cidr, vlan, bonded=False, driver=None):
        network = self.data.get('network')
        if network.get('cidr'):
            raise ValueError('Network is already configured')
        network = {
            'cidr': cidr,
            'vlan': vlan,
            'bonded': bonded,
            'driver': driver
        }
        self._validate_network(network)
        self.data['network'] = network
        self._configure_network()

    def _create_zdb(self, namespace_name, diskname, mountpoint, mode, password, public, size):
        zdb_name = 'zdb_%s_%s' % (self.name, diskname)
        zdb_data = {
            'path': mountpoint,
            'mode': mode,
            'sync': False,
            'namespaces': [
                {
                    'name': namespace_name,
                    'password': password,
                    'public': public,
                    'size': size
                }
            ]
        }

        zdb = self.api.services.find_or_create(ZDB_TEMPLATE_UID, zdb_name, zdb_data)
        zdb.schedule_action('install').wait(die=True)
        zdb.schedule_action('start').wait(die=True)
        return zdb_name

    def create_zdb_namespace(self, disktype, mode, password, public, size, name=''):
        if disktype not in ['HDD', 'SSD']:
            raise ValueError('Disktype should be HDD, SSD')
        if mode not in ['seq', 'user', 'direct']:
            raise ValueError('ZDB mode should be user, direct or seq')

        if disktype == 'HDD':
            disktypes = ['HDD', 'ARCHIVE']
        else:
            disktypes = ['SSD', 'NVME']

        namespace_name = j.data.idgenerator.generateXCharID(10) if not name else name

        potentials = {info['mountpoint']: info['disk'] for info in self.node_sal.zerodbs.partition_and_mount_disks()}
        tasks = []

        zdbs = self.api.services.find(template_uid=ZDB_TEMPLATE_UID)
        for zdb in zdbs:
            tasks.append(zdb.schedule_action('info'))
        results = self._wait_all(tasks, timeout=120, die=True)
        zdbinfo = sorted(list(zip(zdbs, results)), key=lambda x: x[1]['free'],  reverse=True)
        for zdb, info in zdbinfo:
            potentials.pop(info['path'])
        if potentials:
            # there are free disks that are not used lets use them first
            disks = [(self.node_sal.disks.get(diskname), mountpoint) for mountpoint, diskname in potentials.items()]
            disks = list(filter(lambda disk: (disk[0].size / 1024 ** 3) > size and disk[0].type.value in disktypes, disks))
            disks.sort(key=lambda disk: disk[0].size, reverse=True)
            if disks:
                bestfreedisk, mountpoint = disks[0]
                return self._create_zdb(namespace_name, bestfreedisk.name, mountpoint, mode, password, public, size), namespace_name
        zdbinfo = list(filter(lambda info: info[0].data['mode'] == mode and (info[1]['free'] / 1024 ** 3) > size and info[1]['type'] in disktypes, zdbinfo))
        if not zdbinfo:
            message = 'Not enough free space for namespace creation with size {} and type {}'.format(size, ','.join(disktypes))
            raise NoNamespaceAvailability(message)

        for bestzdb, _ in zdbinfo:
            namespaces = [namespace['name'] for namespace in bestzdb.schedule_action('namespace_list').wait(die=True).result]
            if namespace_name not in namespaces:
                kwargs = {
                    'name': namespace_name,
                    'size': size,
                    'password': password,
                    'public': public,
                }
                bestzdb.schedule_action('namespace_create', kwargs).wait(die=True)
                return bestzdb.name, namespace_name

        message = 'Namespace {} already exists on all zerodbs'.format(namespace_name)
        raise NoNamespaceAvailability(message)

    def reboot(self):
        self._stop_all_containers()
        self._stop_all_vms()

        self.logger.info('Rebooting node %s' % self.name)
        self.state.set('status', 'rebooting', 'ok')
        self.node_sal.reboot()

    @timeout(30, error_message='info action timeout')
    def info(self):
        return self.node_sal.client.info.os()

    @timeout(30, error_message='stats action timeout')
    def stats(self):
        return self.node_sal.client.aggregator.query()

    @timeout(30, error_message='processes action timeout')
    def processes(self):
        return self.node_sal.client.process.list()

    @timeout(30, error_message='os_version action timeout')
    def os_version(self):
        return self.node_sal.client.ping()[13:].strip()

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


class NoNamespaceAvailability(Exception):
    pass
