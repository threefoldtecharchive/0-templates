@0x927fb9f82e521ff0;

struct Schema {
    templates @0 :List(Text);
    organization @1 :Text; # optional, if specified enable JWT authentication for this organization
    nics @2 :List(Nic); # Configuration of the attached nics to the container
    dataRepo @3 :Text; # optional, otherwise use default zrobot client data repo
    configRepo @4 :Text; #  optional, otherwise use default zrobot client config repo
    sshkey @5 :Text; # optional if configRepo not sepcified otherwise needed, private sshkey data
    flist @6 : Text; # optional, if not provided it will use the latest release.
    autoPushInterval @7 : Int32; # optional, enables the auto pusher and sets the interval of the auto push
    port @8 : UInt16; # port the created zrobot is listening on

    struct Nic {
        type @0: NicType;
        id @1: Text;
        config @2: NicConfig;
        name @3: Text;
        token @4: Text;
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
}
