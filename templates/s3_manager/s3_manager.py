from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import timeout
from zerorobot.template.state import StateCheckError

S3_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/s3/0.0.1'


class S3Manager(TemplateBase):
    version = '0.0.1'
    template_name = "s3_manager"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self._active_name = '{}_active'.format(self.guid)
        self._passive_name = '{}_passive'.format(self.guid)


    def validate(self):
        if self.data['parityShards'] > self.data['dataShards']:
            raise ValueError('parityShards must be equal to or less than dataShards')

        if len(self.data['minioPassword']) < 8:
            raise ValueError('minio password need to be at least 8 characters')

        if not self.data['minioLogin']:
                raise ValueError('Invalid minio login')
    
        if not self.data['nsPassword']:
            self.data['nsPassword'] = j.data.idgenerator.generateXCharID(32)
    
    def _active_s3(self):
        return self.api.services.get(template_uid=S3_TEMPLATE_UID, name=self._active_name)

    def _passive_s3(self):
        return self.api.services.get(template_uid=S3_TEMPLATE_UID, name=self._passive_name)
        
    def install(self):
        active_data = dict(self.data)
        active_data['nsName'] = self.guid
        active_s3 = self.api.services.find_or_create(S3_TEMPLATE_UID, self._active_name, data=active_data)
        active_s3.schedule_action('install').wait(die=True)
        active_tlog = active_s3.schedule_action('tlog').wait(die=True).result
        nodes = active_s3.schedule_action('namespaces_nodes').wait(die=True).result

        passive_data = dict(active_data)
        passive_data['master'] = active_tlog
        passive_data['masterNodes'] = nodes
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