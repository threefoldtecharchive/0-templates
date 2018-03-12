@0x8c4ee3b29d3ae54d;

struct Schema {
    container @0: Text;           # reference to the container running the tfchain
    node @1: Text;                # reference to the node running the tfchain container
    rpcPort @2: UInt32=23112;     # rpc port of tfchain daemon
    apiPort @3: UInt32=23110;     # http port for tfchain client
    walletSeed @4: Text;
    walletPassphrase @5: Text;
}
