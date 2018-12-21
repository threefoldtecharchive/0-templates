from jumpscale import j
from JumpscaleLib.sal.webgateway.errors import \
    ServiceNotFoundError as WgServiceNotFound
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry

WEB_GATEWAY_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/web_gateway/0.0.1'


class ReverseProxy(TemplateBase):

    version = '0.0.1'
    template_name = 'reverse_proxy'

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.add_delete_callback(self.uninstall)

    def validate(self):
        for key in ['webGateway', 'domain']:
            if not self.data[key]:
                raise ValueError('Invalid value for {}'.format(key))

    def _webgateway_sal(self):
        web_gateway = self.api.services.get(template_uid=WEB_GATEWAY_TEMPLATE_UID, name=self.data['webGateway'])
        web_gateway.state.check('status', 'running', 'ok')
        return j.sal.webgateway.get(self.data['webGateway'])

    @retry(Exception, tries=3, delay=1, backoff=2, logger=None)
    def install(self):
        web_gateway = self._webgateway_sal()
        try:
            service = web_gateway.service_get(self.name)
        except WgServiceNotFound:
            service = web_gateway.service_create(self.name)
        service.expose(self.data['domain'], self.data['servers'])
        self.state.set('actions', 'install', 'ok')

    @retry(Exception, tries=3, delay=1, backoff=2, logger=None)
    def update_servers(self, servers):
        self.state.check('actions', 'install', 'ok')
        self.data['servers'] = servers
        web_gateway = self._webgateway_sal()
        service = web_gateway.service_get(self.name)
        service.proxy.backend_set(servers)
        service.deploy()

    @retry(Exception, tries=3, delay=1, backoff=2, logger=None)
    def uninstall(self):
        try:
            web_gateway = self._webgateway_sal()
            service = web_gateway.service_get(self.name)
            service.delete()
        except (ServiceNotFoundError, WgServiceNotFound):
            # Either web_gateway doesn't exist anymore or the reverse_proxy doesn't exist
            # and in both cases nothing needs to be done
            pass
        self.state.delete('actions', 'install')
