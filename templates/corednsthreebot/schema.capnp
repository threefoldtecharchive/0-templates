@0xd45d35e213c7eefd;

struct Schema {
    nics @0 :List(Nic); # configuration of the attached nics to the traefik container
    ztIdentity @1 :Text; # ztidentity of the container running traefik
    backplane @2 :Text; #the network interface name that will answer dns queries only
    domain @3 :Text; # authorative domain


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
