@0x82a66cb45b1e9ace;



struct Schema {
    memory @0: UInt16 = 128; # Amount of memory in MiB
    cpu @1: UInt16 = 1; # Number of virtual CPUs
    mgmtNic @2: Nic; # zerotier nic to attach to the vm
    image @3: Text; # image name specifying if it is a `zero-os` or `ubuntu` image
    disks @4: List(Disk); # list of disks to attach to the vm
    ports @5 :List(Port); # List of portforwards from node to vm
    configs @6: List(Config); # list of Config
    ztIdentity @7: Text; # VM zerotier ID
    nodeId @8: Text; # the node_id from the capacity registeration of the the node you want to deploy the vm on

   struct Config {
        path @0: Text;
        content @1: Text;
        name @2: Text;
   }

   struct Port {
        source @0: Int32;
        target @1: Int32;
        name @2: Text;
   }

   enum FsType {
        btrfs @0;
        ext4 @1;
        ext3 @2;
        ext2 @3;
   }

   struct Disk {
      diskType @0: DiskType;
      size @1: UInt16;
      mountPoint @2: Text;
      filesystem @3: FsType;
      label @4: Text;
   }

    enum DiskType{
        hdd @0;
        ssd @1;
    }

    struct Nic {
      id @0: Text; # VxLan id or zerotier network id
      type @1: NicType;
      ztClient @2: Text;
      hwaddr @3: Text;
    }

    enum NicType {
      zerotier @0;
    }
}
