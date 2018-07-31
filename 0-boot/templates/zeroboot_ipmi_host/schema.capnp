@0xfefdee2e4b947c50;

struct Schema {
    zerobootClient @0: Text; # Zeroboot client instance name
    ipmiClient @1: Text; # ipmi client instance name
    network @2: Text; # Zeroboot network that contains the host
    mac @3: Text; # Target mac address
    ip @4: Text; # Target IP address
    hostname @5: Text; # Hostname of target
    lkrnUrl @6: Text; # URL to LKRN file with ipxe boot configuration
    powerState @7: Bool; # Internally saved powerstate
}
