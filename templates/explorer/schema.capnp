@0xd01b2137b77c8344;

struct Schema {
    node @0: Text;                # reference to the node running the tfchain container
    rpcPort @1: UInt32=23112;     # rpc port of tfchain daemon
    apiPort @2: UInt32=23110;     # http port for tfchain client
    domain @3: Text; # domain name where to expose the explorer web page
    network @4: Text="standard"; # network to join
    tfchainFlist @5: Text="https://hub.gig.tech/tfchain/ubuntu-16.04-tfchain-latest.flist"; # flist to use for tfchain
    explorerFlist @6: Text="https://hub.gig.tech/tfchain/caddy-explorer-latest.flist"; # flist to use for explorer
    macAddress @7: Text; # mac address for the macvlan interface
    parentInterface @8: Text="";     # parent interface for macvlan, if not set then discovered automatically
}
