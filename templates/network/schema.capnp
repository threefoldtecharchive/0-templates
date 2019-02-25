@0xa70dbb7d55e11f7b;

struct Schema {
    cidr @0: Text; # CIDR to be used for backend network
    vlan @1: Int32; # VlanTag to be used for vxlan traffic
    bonded @2: Bool; # should the backend be bonded over 2 interfaces? @optional
    driver @3: Text; # will ensure kernel module is loaded and interfaces are up @optional
    testIps @4: List(Text); # a list of test ip used by the monitor routine, network assumed broken if not pingable
    mtu @5: Int32; # mtu of backplane optional (default 9000)
    mode @6: Text="ovs"; # optional configuration mode ovs, or native (default ovs)
    lacp @7: Bool; # when using ovs mode and bonding, enable lacp or not
    balanceMode @8: BalanceMode;
    usedInterfaces @9: List(Text); # interfaces that have been configure, this is filled by the template
    interfaces @10: List(Text); # if you don't want the service to auto discover the interfaces, you can pass them explicitly here

    enum BalanceMode{
        slb @0;
        tcp @1;
    }
}
