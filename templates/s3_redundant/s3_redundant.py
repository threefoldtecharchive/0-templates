from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import timeout
from zerorobot.template.state import (SERVICE_STATE_ERROR, SERVICE_STATE_OK,
                                      SERVICE_STATE_SKIPPED,
                                      SERVICE_STATE_WARNING,
                                      StateCategoryNotExistsError,
                                      StateCheckError)

S3_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/s3/0.0.1'
REVERSE_PROXY_UID = 'github.com/threefoldtech/0-templates/reverse_proxy/0.0.1'


class S3Redundant(TemplateBase):
    version = '0.0.1'
    template_name = "s3_redundant"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.recurring_action('_monitor', 60)  # every 60 seconds

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
        try:
            return self.api.services.get(template_uid=S3_TEMPLATE_UID, name=self.data['activeS3'])
        except ServiceNotFoundError:
            self.data['activeS3'] = ''
            raise

    def _passive_s3(self):
        try:
            return self.api.services.get(template_uid=S3_TEMPLATE_UID, name=self.data['passiveS3'])
        except ServiceNotFoundError:
            self.data['passiveS3'] = ''
            raise

    def _handle_data_shard_failure(self, active, passive):
        # handle data failure in the active node then update the namespaces in the passive node
        self.logger.info("Handling data shard failure")
        active.schedule_action('_handle_data_shard_failure').wait(die=True)
        namespaces = active.schedule_action('namespaces').wait(die=True).result
        passive.schedule_action('_update_namespaces', {'namespaces': namespaces}).wait(die=True)

    def _handle_active_tlog_failure(self):
        """
        If master tlog failed we need to promote the passive and redeploy
        a new passive

        Note: there is only one tlog server associated with a node
        so address is not really useful
        """
        self._promote()

    def _handle_passive_tlog_failure(self):
        """
        If passive tlog failed we need to redeploy a new passive node

        Note: there is only one tlog server associated with a node
        so address is not really useful
        """
        active = self._active_s3()
        passive = self._passive_s3()
        passive.schedule_action('redeploy', {'exclude_nodes':
                                             [active.data['minioLocation']['nodeId']]}).wait(die=True)

    def _monitor(self):
        try:
            self.state.check('actions', 'install', 'ok')
        except StateCheckError:
            return

        active_s3 = self._active_s3()
        passive_s3 = self._passive_s3()
        active_running = False
        passive_running = False

        # first check the state of the 2 minios
        try:
            active_s3.state.check('status', 'running', 'ok')
            active_running = True
        except StateCheckError:
            active_running = False

        try:
            passive_s3.state.check('status', 'running', 'ok')
            passive_running = True
        except StateCheckError:
            passive_running = False

        # both minios are down, just redeploy both but preserve the active tlog
        if not passive_running and not active_running:
            active_s3.schedule_action('redeploy', args={'reset_tlog': False}).wait(die=True)
            passive_s3.schedule_action(
                'redeploy', {'exclude_nodes': [active_s3.data['minioLocation']['nodeId']]}).wait(die=True)
            return

        # only passive is down, redeploy it
        if not passive_running:
            passive_s3.schedule_action(
                'redeploy', {'exclude_nodes': [active_s3.data['minioLocation']['nodeId']]}).wait(die=True)
            return

        # active is down, promote the passive and redeploy a minio for the old active
        if not active_running:
            self._promote()
            return

        # if both minios are running fine, check the states shards
        try:
            if SERVICE_STATE_ERROR in list(active_s3.state.get('data_shards').values()):
                self._handle_data_shard_failure(active_s3, passive_s3)
        except StateCategoryNotExistsError:
            pass

        try:
            if SERVICE_STATE_ERROR in list(active_s3.state.get('tlog_shards').values()):
                self._handle_active_tlog_failure()
        except StateCategoryNotExistsError:
            pass

        try:
            if SERVICE_STATE_ERROR in list(passive_s3.state.get('tlog_shards').values()):
                self._handle_passive_tlog_failure()
        except StateCategoryNotExistsError:
            pass

    def _promote(self):
        active_s3 = self._active_s3()
        passive_s3 = self._passive_s3()
        old_active = self.data['activeS3']
        old_passive = self.data['passiveS3']
        passive_s3.schedule_action('promote').wait(die=True)
        self.data['passiveS3'] = old_active
        self.data['activeS3'] = old_passive
        self.save()

        self._update_reverse_proxy_servers()

        master_tlog = passive_s3.schedule_action('tlog').wait(die=True).result
        active_s3.schedule_action('update_master', args={'master': master_tlog}).wait(die=True)
        active_s3.schedule_action(
            'redeploy', {'exclude_nodes': [passive_s3.data['minioLocation']['nodeId']]}).wait(die=True)

    def _update_reverse_proxy_servers(self):
        urls = self._active_s3().schedule_action('url').wait(die=True).result
        try:
            reverse_proxy = self.api.services.get(template_uid=REVERSE_PROXY_UID, name=self.data['reverseProxy'])
            reverse_proxy.schedule_action('update_servers', args={'servers': [urls['storage']]})
        except ServiceNotFoundError:
            self.logger.warning('Failed to find  and update reverse_proxy {}'.format(self.data['reverseProxy']))

    def install(self):
        self.logger.info('Installing s3_redundant {}'.format(self.name))
        active_data = dict(self.data)
        active_data['nsName'] = self.guid
        if self.data['activeS3']:
            active_s3 = self._active_s3()
        else:
            active_s3 = self.api.services.create(S3_TEMPLATE_UID, data=active_data)
            self.data['activeS3'] = active_s3.name
        active_s3.schedule_action('install').wait(die=True)
        self.logger.info('Installed s3 {}'.format(active_s3.name))

        if self.data['passiveS3']:
            passive_s3 = self._passive_s3()
        else:
            active_tlog = active_s3.schedule_action('tlog').wait(die=True).result
            namespaces = active_s3.schedule_action('namespaces').wait(die=True).result
            passive_data = dict(active_data)
            passive_data['master'] = active_tlog
            passive_data['namespaces'] = namespaces
            passive_data['excludeNodes'] = [active_s3.data['minioLocation']['nodeId']]
            passive_s3 = self.api.services.create(S3_TEMPLATE_UID, data=passive_data)
            self.data['passiveS3'] = passive_s3.name
        passive_s3.schedule_action('install').wait(die=True)
        self.logger.info('Installed s3 {}'.format(passive_s3.name))

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

        self.data['passiveS3'] = ''
        self.data['activeS3'] = ''

        self.state.delete('actions', 'install')

    def urls(self):
        self.state.check('actions', 'install', 'ok')
        active_task = self._active_s3().schedule_action('url')
        passive_task = self._passive_s3().schedule_action('url')
        for task in [active_task, passive_task]:
            task.wait(die=True)
        return {
            'active_urls': active_task.result,
            'passive_urls': passive_task.result,
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

    def update_reverse_proxy(self, reverse_proxy):
        self.data['reverseProxy'] = reverse_proxy
        try:
            self.state.check('actions', 'install', 'ok')
        except StateCheckError:
            return
        self._update_reverse_proxy_servers()
