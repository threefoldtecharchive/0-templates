@0xd060778b353684f1;


struct Schema {
    farmerIyoOrg  @0: Text; # the farmer to create the etcds on
    nrEtcds @1 :Int32; # number of etcds in cluster
    etcds @2 :List(Etcd); # list of etcd services. This is set by the template to keep track of all etcds belonging to this cluster
    nics @3 :List(Nic); # Configuration of the attached nics to the etcd instances
    token @4 :Text; # cluster token
    password @5 :Text; # etcd password
    clusterConnections @6 :List(Text);

    struct Etcd {
      name @0: Text; # etcd service name
      node @1: Text; # node id of the node on which the etcd was created
      url @2: Text; # node zrobot url
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
    }
}