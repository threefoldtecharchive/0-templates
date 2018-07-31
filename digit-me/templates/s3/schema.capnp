@0xf35b28a27d2d7444;

struct Schema {
    vmZerotier @0: Zerotier;
    farmerIyoOrg  @1: Text; # the farmer to create the s3 on
    dataShards @2: Int32=1; # 0-stor data shards config
    parityShards @3: Int32; # 0-stor parity shards config
    storageType @4: StorageType; # s3 storage type
    storageSize @5: UInt16; # s3 storage size
    namespaces @6: List(Namespace); # namespace services created for s3. This is set by the template.
    minioLogin @7: Text; # minio login
    minioPassword @8: Text; # minio password
    minioUrl @9: Text; # url to access minio on. This is set by the template.

    enum StorageType {
     hdd @0;
     ssd @1;
    }

    struct Zerotier {
      id @0: Text; # zerotier network the vm should join
      ztClient @1: Text; # the zt client service to be used to authorize the vm
    }

    struct Namespace {
    name @0: Text; # namespace service name
    node @1: Text; # node id of the node on which the namespace was created
    url @2: Text; # node zrobot url
    }
}

