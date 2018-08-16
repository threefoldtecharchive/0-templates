@0xfefdee2e4b947c50;

struct Schema {
    zerobootClient @0: Text; # Zeroboot client instance name
    ipmiClient @1: Text; # ipmi client instance name
    mac @2: Text; # Target mac address
    ip @3: Text; # Target IP address
    hostname @4: Text; # Hostname of target
    lkrnUrl @5: Text; # URL to LKRN file with ipxe boot configuration
    powerState @6: Bool; # Internally saved powerstate
}
