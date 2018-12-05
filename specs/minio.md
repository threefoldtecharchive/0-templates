# Templates to deploy Minio

Architecture:

[![https://docs.google.com/drawings/d/e/2PACX-1vTaGDkWAAotE7QlECby7vDN-hovgNMi0o2fMBMkZ3UCQVAHoiKXi51rgua0X3AKtxWb5_5HCJMpdyp8/pub?w=1440&h=1080](https://docs.google.com/drawings/d/e/2PACX-1vTaGDkWAAotE7QlECby7vDN-hovgNMi0o2fMBMkZ3UCQVAHoiKXi51rgua0X3AKtxWb5_5HCJMpdyp8/pub?w=1440&h=1080)](https://docs.google.com/drawings/d/e/2PACX-1vTaGDkWAAotE7QlECby7vDN-hovgNMi0o2fMBMkZ3UCQVAHoiKXi51rgua0X3AKtxWb5_5HCJMpdyp8/pub?w=1440&h=1080)

## IT Robot level

### Minio 
This template is responsible to manage the creation of a new minio service.
It will receive capacity reservation an detail about how much storage is require to provide to minio as well as the list of farming pool to use from the User robot

It will then create a 'minio reservation' services on the required farming robot.

#### actions
- init (creation of the service)
  - schema:
    - size: capacity to provision in GiB
    - famring pools: list of address of farming robot to use to provision
    - ... any other info minio requires to start ?

- set_connection_info: called by the minio deployed on the node to set tell the IT robot how to access minio

## Farming robot

### Minio reservation
This template it responsible to create everything requires to run minio: filesystem on disk, containers, minio process.
Based on the amount of storage required, this service will decide on which node to deploy the different components

#### schema
- nodes: list of node used
- size: storage capacity for minio in GiB
- ...

#### action
- init : will create make sure there is a filesystem on the disks, create the container for 0-db, create container for minio and start it
- start : start minio after it has been stopped
- stop: stop minio
- monitor: check health of the process as well as all the 0-db processes

## Node robot
This robot role is to received service creation request from the minio reservation service.
It will hold the service for each container/process/... deployed.
Also, once minio is deployed, the IT robot can talk directly to the minio service of this robot.
