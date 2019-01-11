@0xb6532701946c636f;


struct Schema {
    nics @0 :List(Nic); # Configuration of the attached nics to the etcd container
    ztIdentity @1 :Text; # ztidentity of the container running 0-etcd
    token @2 :Text; # cluster token
    cluster @3 :Text; #  a string of the cluster connection info, used in the etcd conf `initial-cluster` value ex: `one=http://172.12.53.12:2380,two=172.12.53.13:2380`
    password @4 :Text; # etcd root user password
    hostNetwork @5 :Bool; # if true, etcd container will use host networking

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
    }
}
