@0x8f4e6505afa01c30;

struct Schema {
    nics @0 :List(Nic); # Configuration of the attached nics to the traefik, coredns and etcd containers
    nrEtcds @1 :Int32; # number of etcd instance in the cluster
    etcdPassword @2 :Text; # etcd root user password
    farmerIyoOrg @3 :Text; # farmer for nodes to create etcd instances on
    publicNode @4 :Text; # node to deploy traefik and coredns on

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