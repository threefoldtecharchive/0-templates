from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import timeout
from zerorobot.template.state import StateCheckError

S3_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/s3/0.0.1'


class S3Redundant(TemplateBase):
    version = '0.0.1'
    template_name = "s3_redundant"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.recurring_action('_monitor', 60)  # every 60 seconds
        self.recurring_action('_monitor_vm', 30)

    def validate(self):
        if self.data['parityShards'] > self.data['dataShards']:
            raise ValueError('parityShards must be equal to or less than dataShards')

        if len(self.data['minioPassword']) < 8:
            raise ValueError('minio password need to be at least 8 characters')

        for key in ['minioLogin', 'storageSize']:
            if not self.data[key]:
                raise ValueError('Invalid value for {}'.format(key))

        if not self.data['nsPassword']:
            self.data['nsPassword'] = j.data.idgenerator.generateXCharID(32)

    def _active_s3(self):
        return self.api.services.get(template_uid=S3_TEMPLATE_UID, name=self.data['activeS3'])

    def _passive_s3(self):
        return self.api.services.get(template_uid=S3_TEMPLATE_UID, name=self.data['passiveS3'])

    def _handle_data_shard_failure(self, active, passive, address):

        # handle data failure in the active node then update the namespaces in the passive node
        active.schedule_action('_handle_data_shard_failure', {'connection_info': address}).wait(die=True)
        namespaces = active.schedule_action('namespaces').wait(die=True).result
        passive.schedule_action('_update_namespaces', {'namespaces': namespaces})

    def _monitor(self):
        # for data zdb, we only watch the active s3
        active = self._active_s3()
        passive = self._passive_s3()

        for address, state in active.state.get('data_shards', {}).items():
            if state == 'ok':
                continue

            self._handle_data_shard_failure(active, passive, address)

        for address, state in active.state.get('tlog_shards', {}).items():
            if state == 'ok':
                continue

            # TODO: kick start the promote logic, and destroy current active setup

        for address, state in passive.state.get('tlog_shards', {}).items():
            if state == 'ok':
                continue

            # TODO: destroy passive setup and recreate

    def _monitor_vm(self):
        try:
            self.state.check('actions', 'install', 'ok')
        except StateCheckError:
            return
        self.logger.info('Monitor s3 redundant vms %s' % self.name)
        active_s3 = self._active_s3()
        passive_s3 = self._passive_s3()
        try:
            active_s3.state.check('vm', 'running', 'ok')
            active = True
        except StateCheckError:
            active = False
        try:
            passive_s3.state.check('vm', 'running', 'ok')
            passive = True
        except StateCheckError:
            passive = False

        # both vms are down, just redeploy both vms but preserve the active tlog
        if not passive and not active:
            active_s3.schedule_action('redeploy', args={'reset_tlog': False}).wait(die=True)
            passive_s3.schedule_action('redeploy').wait(die=True)
            return

        # only passive is down, redeploy its vm
        if not passive:
            passive_s3.schedule_action('redeploy').wait(die=True)

        # active is down, promote the passive and redeploy a vm for the old active
        if not active:
            old_active = self.data['activeS3']
            old_passive = self.data['passiveS3']
            passive_s3.schedule_action('promote').wait(die=True)
            master_tlog = passive_s3.schedule_action('tlog').wait(die=True).result
            active_s3.schedule_action('update_master', args={'master': master_tlog}).wait(die=True)
            active_s3.schedule_action('redeploy').wait(die=True)

            self.data['passiveS3'] = old_active
            self.data['activeS3'] = old_passive

    def install(self):
        active_data = dict(self.data)
        active_data['nsName'] = self.guid
        if self.data['activeS3']:
            active_s3 = self._active_s3()
        else:
            active_s3 = self.api.services.create(S3_TEMPLATE_UID, data=active_data)
            self.data['activeS3'] = active_s3.name
        active_s3.schedule_action('install').wait(die=True)

        if self.data['passiveS3']:
            passive_s3 = self._passive_s3()
        else:
            active_tlog = active_s3.schedule_action('tlog').wait(die=True).result
            namespaces = active_s3.schedule_action('namespaces').wait(die=True).result
            passive_data = dict(active_data)
            passive_data['master'] = active_tlog
            passive_data['namespaces'] = namespaces
            passive_s3 = self.api.services.create(S3_TEMPLATE_UID, data=passive_data)
        passive_s3.schedule_action('install').wait(die=True)
        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        s3s = [self._active_s3, self._passive_s3]
        tasks = []
        services = []
        for s3 in s3s:
            try:
                self.logger.info("uninstall and delete s3")
                service = s3()
                tasks.append(service.schedule_action('uninstall'))
                services.append(service)
            except ServiceNotFoundError:
                pass

        for task in tasks:
            task.wait(die=True)

        for service in services:
            service.delete()

        self.state.delete('actions', 'install')

    def urls(self):
        self.state.check('actions', 'install', 'ok')
        active_urls = self._active_s3().schedule_action('url').wait(die=True).result
        passive_urls = self._passive_s3().schedule_action('url').wait(die=True).result
        return {
            'active_urls': active_urls,
            'passive_urls': passive_urls,
        }

    def start_active(self):
        self.state.check('actions', 'install', 'ok')
        active_s3 = self._active_s3()
        active_s3.schedule_action('start').wait(die=True)

    def stop_active(self):
        self.state.check('actions', 'install', 'ok')
        active_s3 = self._active_s3()
        active_s3.schedule_action('stop').wait(die=True)

    def upgrade_active(self):
        self.stop_active()
        self.start_active()

    def start_passive(self):
        self.state.check('actions', 'install', 'ok')
        passive_s3 = self._passive_s3()
        passive_s3.schedule_action('start').wait(die=True)

    def stop_passive(self):
        self.state.check('actions', 'install', 'ok')
        passive_s3 = self._passive_s3()
        passive_s3.schedule_action('stop').wait(die=True)

    def upgrade_passive(self):
        self.stop_passive()
        self.start_passive()

    def get_etcd_client(self):
        pass

    def get_active_ip(self):
        return self._active_s3().data['mgmtNic']['ip']

    def get_passive_ip(self):
        return self._passive_s3().data['mgmtNic']['ip']

    def handle_active_minio_tlog_failure(self, minio_active):
        # minio template needs to watch the logs from minio process and in the cases where it see minio cannot access or some IO error happens on the tlog zdb namespace.

        # Example flow:

        # Minio output some logs showing it cannot reach the tlog shard
        # minio template see these logs
        # minio template update it's state to be marked as unhealthy
        # s3 template detect minio state is unhealthy
        # we need to find a way for minio and s3 template to exchange the information about which shards is unreachable (TODO)
        # s3 template checks the zdb namespace states
        # if it can just restart it -> restart it
        # if disk is really dead
        # The reverse proxy stops serving requests to the broken minio VM and starts forwarding requests to the passive minio VM which then becomes the active minio
        # reserve a new namespace on a new disk
        # update minio configration with new tlog shard and making this minio the passive one
        # minio service send signal to minio process to ask to reload its config
        # minio process will then start replicating new metadata from the active minio
        pass

    def handle_passive_minio_tlog_failure(self, minio_passive):
        # minio template needs to watch the logs from minio process and in the cases where it see minio cannot access or some IO error happens on the tlog zdb namespace.

        # Example flow:

        # Minio output some logs showing it cannot reach the tlog shard
        # minio template see these logs
        # minio template update it's state to be marked as unhealthy
        # s3 template detect minio state is unhealthy
        # we need to find a way for minio and s3 template to exchange the information about which shards is unreachable (TODO)
        # s3 template checks the zdb namespace states
        # if it can just restart it -> restart it
        # if disk is really dead
        # reserve a new namespace on a new disk
        # update minio configration with new tlog shard
        # minio service send signal to minio process to ask to reload its config
        # minio process will then start replicating new metadata from the active minio on the new tlog shard
        pass

    def handle_minio_data_disk_failure(self):

        # minio template needs to watch the logs from minio process and in the cases where it see minio cannot access some shards or some IO error happens, the robot needs to take actions.

        # Example flow:

        # Minio output some logs showing it cannot reach some shards (threefoldtech/minio#16)
        # minio template see these logs
        # minio template update it's state to be marked as unhealthy
        # s3 template detect minio state is unhealthy
        # we need to find a way for minio and s3 template to exchange the information about which shards is unreachable (TODO)
        # s3 template checks the zdb namespace states
        # if it can just restart it -> restart it
        # if disk is really dead, reserve a new namespace on a new disk -> update minio configration with new shards -> minio service send signal to minio process to ask to reload its config -> ask minio to start healing proces to write missing data on the new shards
        pass
