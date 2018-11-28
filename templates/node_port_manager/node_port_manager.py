from jumpscale import j
from zerorobot.template.base import TemplateBase


NODE_CLIENT = 'local'


class NodePortManager(TemplateBase):

    version = '0.0.1'
    template_name = 'node_port_manager'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.node_sal = j.clients.zos.get(NODE_CLIENT)
        self.recurring_action('_cleanup', 30)  # every 30 seconds

    def validate(self):
        services = self.api.services.find(template_name='node_port_manager')
        if services and services[0].guid != self.guid:
            raise RuntimeError('Another node_port_manager service exists. Only one service per node is allowed')

    def _cleanup(self):
        """
        recurring action that remove reservation of port
        of services that doesn't exist anymore.

        It can happens that some service are deleted without properly releasing their port
        this method will make sure that all port reserve for non existing services
        are released automatically
        """
        self.logger.info("port manager: start clean up reserved ports")
        services_guids = self.api.services.guids.keys()
        for item in list(self.data['ports']):
            if item['serviceGuid'] not in services_guids:
                self.logger.info("release port %s that was reserved by %s", item['port'], item['serviceGuid'])
                self.data['ports'].remove(item)

    def reserve(self, service_guid, n=1):
        used_ports = [x['port'] for x in self.data['ports']]
        selected_ports = []

        for _ in range(n):
            port = self._reserve(exclude=used_ports)
            used_ports.append(port)
            selected_ports.append(port)
            self.data['ports'].append({'port': port, 'serviceGuid': service_guid})

        self.save()
        return selected_ports

    def release(self, service_guid, ports):
        for item in list(self.data['ports']):
            if item['port'] in ports:
                if item['serviceGuid'] != service_guid:
                    raise RuntimeError("only service that reserved a port can release it")
                self.data['ports'].remove(item)
        self.save()

    def _reserve(self, exclude):
        port = self.node_sal.freeports(1)[0]
        while port in exclude:
            # this will eventually raised if no port is found
            port = self.node_sal.freeports(1)[0]
        #  if we reached here, we found a free port
        return port
