@0xb1e322af4c1787e4;

struct Schema {
    etcdEndpoint @0 :Text; # etcd endpoint
    etcdWatch @1 :Bool=true; # watch changes in Traefik web 
    etcdPassword @2 :Text; # etcd root user password
    nics @3 :List(Nic); # Configuration of the attached nics to the traefik container
    ztIdentity @4 :Text; # ztidentity of the container running traefik

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
