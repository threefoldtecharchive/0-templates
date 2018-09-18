@0xf35b28a27d2d7444;

struct Schema {
    mgmtNic @0: Nic; # zerotier management nic
    farmerIyoOrg  @1: Text; # the farmer to create the s3 on
    dataShards @2: Int32=16; # 0-stor data shards config
    parityShards @3: Int32=4; # 0-stor parity shards config
    storageType @4: StorageType; # s3 storage type
    storageSize @5: UInt16; # s3 storage size
    namespaces @6: List(Namespace); # namespace services created for s3. This is set by the template.
    minioLogin @7: Text; # minio login
    minioPassword @8: Text; # minio password
    minioUrl @9: Text; # url to access minio on. This is set by the template.
    nsPassword @10: Text; # Namespace password



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

