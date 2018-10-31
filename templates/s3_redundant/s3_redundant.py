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
        self._active_name = '{}_active'.format(self.guid)
        self._passive_name = '{}_passive'.format(self.guid)

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
        return self.api.services.get(template_uid=S3_TEMPLATE_UID, name=self._active_name)

    def _passive_s3(self):
        return self.api.services.get(template_uid=S3_TEMPLATE_UID, name=self._passive_name)

    def _monitor(self):
        # for data zdb, we only watch the active s3
        active = self._active_s3()
        passive = self._passive_s3()
        
        state = active.state
        for address, state in state.get('data_shards', {}):
            if state == 'ok':
                continue
            
            job = active.schedule_action('_handle_data_shard_failure', {'connection_info': connection_info})
            namespace_info = job.wait(die=True).result
            if namespace_info['address'] == connection_info:
                continue
            
            # we set this new shard on both active and passive
            active.schedule_action('_update_namespace', {'address': address, 'namespace': namespace_info})
            passive.schedule_action('_update_namespace', {'address': address, 'namespace': namespace_info})

    def install(self):
        active_data = dict(self.data)
        active_data['nsName'] = self.guid
        active_s3 = self.api.services.find_or_create(S3_TEMPLATE_UID, self._active_name, data=active_data)
        active_s3.schedule_action('install').wait(die=True)
        active_tlog = active_s3.schedule_action('tlog').wait(die=True).result
        namespaces = active_s3.schedule_action('namespaces').wait(die=True).result

        passive_data = dict(active_data)
        passive_data['master'] = active_tlog
        passive_data['namespaces'] = namespaces
        passive_s3 = self.api.services.find_or_create(S3_TEMPLATE_UID, self._passive_name, data=passive_data)
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
