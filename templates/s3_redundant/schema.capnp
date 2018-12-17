@0xb196bec31874023a;


struct Schema {
    mgmtNic @0 :Nic; # zerotier management nic
    farmerIyoOrg  @1 :Text; # the farmer to create the s3 on
    dataShards @2 :Int32=16; # 0-stor data shards config
    parityShards @3 :Int32=4; # 0-stor parity shards config
    storageType @4 :StorageType; # s3 storage type
    storageSize @5 :UInt64; # total s3 storage size in GB
    minioLogin @6 :Text; # minio login
    minioPassword @7 :Text; # minio password
    minioBlockSize @8 :UInt32=1048576; # minio data block size in bytes
    nsPassword @9: Text; # Namespace password
    activeS3 @10 :Text; # name of the active s3 service
    passiveS3 @11 :Text; # name of passive s3 service
    reverseProxy @12 :Text; #name of the reverse proxy service to update

    enum StorageType {
     hdd @0;
     ssd @1;
    }

    struct Nic {
      id @0: Text; # Zerotier network id
      ztClient @1: Text;
    }
}

