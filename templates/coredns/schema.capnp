@0xaf3b04a861b5a7f1;

struct Schema {
    etcdEndpoint @0 :Text; # etcd endpoint
    etcdPassword @1 :Text; # etcd root user password
    nics @2 :List(Nic); # configuration of the attached nics to the traefik container
    ztIdentity @3 :Text; # ztidentity of the container running traefik
    backplane @4 :Text="backplane"; #the network interface name that will answer dns queries only


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
