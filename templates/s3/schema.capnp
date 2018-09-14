@0xf35b28a27d2d7444;

struct Schema {
    mgmtNic @0: Nic; # zerotier management nic
    storageNic @1: Text; # vxlan management nic
    farmerIyoOrg  @2: Text; # the farmer to create the s3 on
    dataShards @3: Int32=16; # 0-stor data shards config
    parityShards @4: Int32=4; # 0-stor parity shards config
    storageType @5: StorageType; # s3 storage type
    storageSize @6: UInt16; # s3 storage size
    namespaces @7: List(Namespace); # namespace services created for s3. This is set by the template.
    minioLogin @8: Text; # minio login
    minioPassword @9: Text; # minio password
    minioUrl @10: Text; # url to access minio on. This is set by the template.
    gateway @11: Text; # Gateway service to use for vm
    gatewayRobot @12: Text; # Robot that created the gaty
    gatewayPublicNetwork @13: Text; # Gateway network to use for the vm
    gatewayPrivateNetwork @14: Text; # Gateway network to use for the vm
    nsPassword @15: Text; # Namespace password
    vmMacaddress @16: Text; # vm macaddress retrieved from the gateway
    vmIp @17: Text; # Vm ip retrieved from the gateway
    vmPort @18: Int32; # Vm forward port retrieved from the gateway



    enum StorageType {
     hdd @0;
     ssd @1;
    }

    struct Nic {
      id @0: Text; # Zerotier network id
      ztClient @1: Text;
    }

    struct Namespace {
    name @0: Text; # namespace service name
    node @1: Text; # node id of the node on which the namespace was created
    url @2: Text; # node zrobot url
    }
}

