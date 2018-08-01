# Digital me

Digital me is a set of service tempaltes that can work together to accomplish some tasks on the TF Grid. Checkout out [0-robot](https://github.com/zero-os/0-robot) for details
on how templates are used.

## Operation of the templates
All the digital me templates should (on a low level) create some prmitive services on the TF Grid, by asking farmer/reservation robots for these low
level primiteves. The digital me templates will directly manage the provisioned resources to buil high level services like VMs, S3, K8S, etc ...

Once a primitive service is provisioned the template instance that asked for it should keep access credentials and location on the grid for further orchestration. Note, that the farmer/reservation robot MUST NOT keep local credential of the primitive, only the digital.me robot who asked for the
service to be provisioned will know how to access it.

> TODO: How to pass service credentials back to digital.me directly from a node robot without going over reservation robot?

To accomplish this, a proxy service for the primitives must be implemented and created by digital.me robot, here is a list with the primitives that
are available on ande zero-os node.

## Proxy services
- **VM** (ubuntu, zos) from an flist
- **0-DB** for storage
- **0-GW** for networking

### Proxy service operation
Once a proxy service is `installed` a request is made to the farmer/reservation to install an actual instance of the service. The proxy
service will proxy subsequent operation to the right node/service.

The proxy service must remember all the attributes it needs to reach and operate on the remote service this can include:
- Reservation robot who handled the request
- Node robot for direct resource management
- Address of the service. This can be different for different service types. (for example, ssh address of a VM, or IP:PORT for 0-db)
- Access Keys and/or username/password combos

## Higher level services
Higher level services will only deal with proxy services. In other words, it applies it's functionality by creating and mainting the local proxy service
to create and maintain services that runs on the TF Grid. The high end service, does not care (nor it should) where the actual services run, since it deals
with all the low level components via the proxy.

A list of possible high end services are:
- S3 storage
- VM ?

## Higher level service operation
On creation of a high level service, it uses it's configuration to compute the type and amount of low level resources it needs to reach the required
deployment state.

Based on that, it creates and deploy the low level services proxies, that will do the actual request for the reservation AND track the access to the actual
deployed service.

After preparation of the low level services, the high level service, will continue the deployment by deplying and starting the software that requires to
run the actual work load. For examples, `apt-get install` for ubuntu, or `containers` for zos.

