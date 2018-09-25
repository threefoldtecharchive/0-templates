@0xb6532701946c636f;


struct Schema {
    nics @0 :List(Nic); # Configuration of the attached nics to the etcd container
    ztIdentity @1 :Text; # ztidentity of the container running 0-etcd
    token @2 :Text;
    cluster @3 :List(Member);

    struct Member {
        name @0 :Text;
        address @1 :Text;
    }

    struct Nic {
        type @0 :NicType;
        id @1 :Text;
        config @2 :NicConfig;
        name @3 :Text;
        ztClient @4 :Text;
        hwaddr @5 :Text;
    }

    struct NicConfig {
        dhcp @0 :Bool;
        cidr @1 :Text;
        gateway @2 :Text;
        dns @3 :List(Text);
    }

    enum NicType {
        default @0;
        zerotier @1;
        vlan @2;
        vxlan @3;
        bridge @4;
    }
}
