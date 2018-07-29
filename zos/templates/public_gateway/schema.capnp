@0xc9d615ef1c6d1fb9;


struct Schema {
    portforwards @0: List(PortForward);
    httpproxies @1: List(HTTPProxy);

    enum HTTPType {
        http @0;
        https @1;
    }

    struct HTTPProxy {
        host @0: Text;
        destinations @1: List(Text);
        types @2: List(HTTPType);
        name @3: Text;
    }

    enum Status{
        halted @0;
        running @1;
    }

    enum IPProtocol{
        tcp @0;
        udp @1;
    }

    struct PortForward{
        protocols @0: List(IPProtocol);
        srcport @1: Int32;
        dstport @2: Int32;
        dstip @3: Text;
        name @4: Text;
    }
}
