@0xd01b2137b77c8344;

struct Schema {
    node @0: Text;                # reference to the node running the tfchain container
    rpcPort @1: UInt32=23112;     # rpc port of tfchain daemon
    apiPort @2: UInt32=23110;     # http port for tfchain client
    domain @3: Text; # domain name where to expose the explorer web page
    network @4: Text="standard"; # network to join
}
