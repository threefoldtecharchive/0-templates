@0xbe3b7b68c86b357e;

struct Schema {
    hostname @0 :Text;
    networks @1 :List(Network); # Configuration of the attached nics to the container
    portforwards @2 :List(PortForward);
    httpproxies @3 :List(HTTPProxy);
    domain @4: Text;
    nodeId @5: Text;
    publicGatewayRobot @6: Text;

    struct Network {
        type @0: NetworkType;
        id @1: Text;
        config @2: NetworkConfig;
        name @3: Text;
        dhcpserver @4: DHCP;
        ztClient @5: Text;
    }

    struct CloudInit {
        userdata @0: Text;
        metadata @1: Text;
    }

    struct Host {
        macaddress @0: Text;
        hostname @1: Text;
        ipaddress @2: Text;
        ip6address @3: Text;
        cloudinit @4: CloudInit;
    }

    struct DHCP {
        nameservers @0: List(Text);
        hosts @1: List(Host);
        poolStart @2: Int32;
        poolSize @3: Int32;
    }

    struct NetworkConfig {
        cidr @0: Text;
        gateway @1: Text;
    }

    enum HTTPType {
        http @0;
        https @1;
    }

    struct HTTPProxy {
        host @0: Text;
        destinations @1: List(HTTPDestination);
        types @2: List(HTTPType);
        name @3: Text;
    }

    struct HTTPDestination {
        vm @0: Text;
        port @1: Int32;
    }

    enum IPProtocol{
        tcp @0;
        udp @1;
    }

    struct PortForward{
        protocols @0: List(IPProtocol);
        srcport @1: Int32;
        dstport @2: Int32;
        vm @3: Text;
        name @4: Text;
    }
    enum NetworkType {
        default @0;
        zerotier @1;
        vlan @2;
        vxlan @3;
        bridge @4;
        passthrough @5;
    }
    struct Certificate{
      path @0: Text;
      key @1: Text;
      metadata @2: Text;
      cert @3: Text;
    }
}
