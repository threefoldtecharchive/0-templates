@0xfefdee2e4b947c50;

struct Schema {
    zerobootClient @0: Text; # Zeroboot client instance name
    racktivities @1: List(Racktivity); # Racktivity devices settings
    mac @2: Text; # Target mac address
    ip @3: Text; # Target IP address
    hostname @4: Text; # Hostname of target
    lkrnUrl @5: Text; # URL to LKRN file with ipxe boot configuration
    powerState @6: Bool; # Internally saved powerstate (Do not provide in init data)
}

struct Racktivity {
    client @0: Text; # Racktivity service/client instance name
    port @1: Text; # Target's port on the Racktivity device
    powermodule @2: Text; # Racktivity module ID (only Racktivity for SE models)
}
