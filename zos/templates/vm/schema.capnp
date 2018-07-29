@0xb87ba7e9ff3d95db;



struct Schema {
    memory @0: UInt16 = 128; # Amount of memory in MiB
    cpu @1: UInt16 = 1; # Number of virtual CPUs
    nics @2: List(Nic); # list of nics to attach to the vm
    flist @3: Text; # flist to boot the vm from
    vnc @4: Int32 = -1; # the vnc port the machine is listening to
    ports @5:List(Port); # List of portforwards from node to vm
    disks @6: List(Disk); # list of disks to attach to the vm
    tags @7: List(Text); # list of tags
    configs @8: List(Config); # list of config
    ztIdentity @9: Text; # VM zerotier ID
    ipxeUrl @10: Text; # ipxe url for zero-os vm
    mounts @11: List(Mount); # list of mounts to mount on the vm

    struct Mount {
        name @0: Text;
        sourcePath @1: Text;
        targetPath @2: Text;
    }

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
    struct Disk {
      url @0: Text;
      name @1: Text;
      mountPoint @2: Text;
      filesystem @3: Text;
      label @4: Text;
    }

    struct Nic {
      id @0: Text; # VxLan or VLan id
      type @1: NicType;
      hwaddr @2: Text;
      name @3: Text;
      ztClient @4: Text;
    }

    enum NicType {
      default @0;
      vlan @1;
      vxlan @2;
      bridge @3;
      zerotier @4;
    }
}
