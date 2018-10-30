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

    def _promote_passive(self):
        self._passive_s3().schedule_action('promote_passive').wait(die=True)

    def get_etcd_client(self):
        pass

    def get_active_ip(self):
        return self._active_s3().data['mgmtNic']['ip']

    def get_passive_ip(self):
        return self._passive_s3().data['mgmtNic']['ip']

    # def handle_active_minio_failure(self):
    #     active_ip = self.get_active_ip()
    #     passive_ip = self.get_passive_ip()

    #     def get_backend_for(ip):
    #         # TODO: move to traefik sal.
    #         pass

    #     def update_backend_ip(backendname, ip):
    #         # update in backend servers...
    #         cl = self.get_etcd_client()
    #         proxy = cl.proxy_create([], [backend])
    #         # write the configuration into etcd
    #         proxy.deploy()
    #         proxy.delete()
    #         pass


    #     etcd_client = self.get_etcd_client()
    #     j.sal.traefik.get("instance_name", data={'etcd_instance':etcd_client.instance})
    #     backend = get_backend_for(active_ip)

    #     update_backend_ip(backend.name, passive_ip)
    #     self.promote_passive()




    #     # The reverse proxy stops serving requests to the broken minio VM
    #     # Update configuration of the passive minio to become the active one
    #     # The reverse proxy starts forwarding requests to the passive minio VM which as becomes the active minio
    #     # Deploy a new minio VM and configure it to be the passive one, replicting metadata from the newly active

    #     pass

    def handle_passive_minio_failure(self):
        # Redeploy a new VM and configure it to be the passive one replicating from the active
        def deploy_passive_minio_for(master_ip):
            pass

        pass

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
