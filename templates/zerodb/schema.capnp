@0xb198f305ed84eb26;


struct Schema {
    mode @0: Mode=direct; # a value from enum Mode representing the 0-db mode
    sync @1: Bool=false; # boolean indicating whether all write should be sync'd or not.
    path @2: Text; # path to use for zdb data. Filled out by the template if it is not supplied.
    admin @3: Text; # admin password
    namespaces @4: List(Namespace); # a list of namespaces deployed on this zerodb
    nics @5 :List(Nic); # Configuration of the attached nics to the zerodb container
    ztIdentity @6: Text; # ztidentity of the container running 0-db
    size @7: Int32; # disk size of the 0-db. Only applicable for ssd.
    diskType @8 :DiskType; # type of disk to use for this zerodb
    nodePort @9 :Int32; # public listening port

    enum DiskType{
        hdd @0;
        ssd @1;
    }

    struct Nic {
        type @0: NicType;
        id @1: Text;
        config @2: NicConfig;
        name @3: Text;
        ztClient @4: Text;
        hwaddr @5: Text;
    }

    struct NicConfig {
        dhcp @0: Bool;
        cidr @1: Text;
        gateway @2: Text;
        dns @3: List(Text);
    }

    enum NicType {
        default @0;
        zerotier @1;
        vlan @2;
        vxlan @3;
        bridge @4;
    }

    enum Mode {
        user @0;
        seq @1;
        direct @2;
    }

    struct Namespace {
        name @0: Text; # name of the namespace
        size @1: Int32; # the maximum size in GB for the namespace
        password @2: Text; # password for the namespace
        public @3: Bool=true; # boolean indicating if it is public or not
    }
}
