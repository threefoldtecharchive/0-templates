@0xba1805e2bd8cb67b;

struct Schema {
    # reference to the node running the tfchain container    
    node @0: Text;
    
    # rpc port of tfchain daemon
    rpcPort @1: UInt32=23112;
    
    # http port for tfchain client
    apiPort @2: UInt32=23110;
    
    walletSeed @3: Text;
    
    walletPassphrase @4: Text;

    # address of the wallet
    walletAddr @5: Text;

    # network to join
    network @6: Text="standard";

    # flist to use for tfchain
    tfchainFlist @7: Text="https://hub.gig.tech/tfchain/ubuntu-16.04-tfchain-latest.flist";
 
    # parent interface for macvlan, if not set then discovered automatically
    parentInterface @8: Text=""; 
}
