@0xba1805e2bd8cb67b;

struct Schema {
    node @0: Text;                # reference to the node running the tfchain container
    rpcPort @1: UInt32=23112;     # rpc port of tfchain daemon
    apiPort @2: UInt32=23110;     # http port for tfchain client
    walletSeed @3: Text;
    walletPassphrase @4: Text;
    walletAddr @5: Text;          # address of the wallet
    network @6: Text="standard";  # network to join
    tfchainFlist @7: Text="https://hub.gig.tech/tfchain/ubuntu-16.04-tfchain-latest.flist"; # flist to use for tfchain
    parentInterface @8: Text;     # parent interface for macvlan, if not set then discovered automatically
}
