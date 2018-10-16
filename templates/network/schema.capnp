@0xa70dbb7d55e11f7b;

struct Schema {
    cidr @0: Text; # CIDR to be used for backend network
    vlan @1: Int32; # VlanTag to be used for vxlan traffic
    bonded @2: Bool; # should the backend be bonded over 2 interfaces? @optional
    driver @3: Text; # will ensure kernel module is loaded and interfaces are up @optional
    testIp @4 Text; # a test ip used by the monitor routine, network assumed broken if not pingable
}
