## template: github.com/threefoldtech/0-templates/node_port_manager/0.0.1

### Description:
This service is automatically installed on the node. You don't need to manually install it

This service is responsible for the management of the port forward of a node.
Any service that wants to do a port forward on the node needs to first reserve the port using the `reserve` action of the port manager.

Once the service that reserved a port is uninstall, it needs to relase the port using the release action of the port manager


Next is an simple example of how a service should use the port manager to reserve a port


```python
# beginning of the code omitted for brevity
def install(self):
    port_mgr = self.api.services.get(PORT_MANAGER_TEMPLATE_UID, '_port_manager')
    self.data['ports'] = port_mgr.schedule_action("reserve", {"service_guid": self.guid, 'n': 1}).wait(die=True).result
    # use the value in free_ports

def uninstall(self):
    # here we release the reserved port that we got in the install method
    port_mgr = self.api.services.get(PORT_MANAGER_TEMPLATE_UID, '_port_manager')
    port_mgr.schedule_action("release", {"service_guid": self.guid, 'ports': self.data['ports']})
```