@0xb6532701946c636f;


struct Schema {
    listenPeerUrls @0 :List(Text); # List of URLs to listen on for peer traffic default: "http://localhost:2380"
    listenClientUrls @1 :List(Text); # List of URLs to listen on for client traffic default: "http://localhost:2379"
    initialAdvertisePeerUrls @2 :List(Text); # List of this member's peer URLs to advertise to the rest of the cluster. default: "http://localhost:2380"
    advertiseClientUrls @3 :List(Text); # List of this member's client URLs to advertise to the rest of the cluster default: "http://localhost:2379"
    nics @4 :List(Nic); # Configuration of the attached nics to the etcd container
    ztIdentity @5 :Text; # ztidentity of the container running 0-etcd
    token @6 :Text;
    cluster @7 :List(Member);

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
