@0xba1805e2bd8cb67b;

struct Schema {
    container @0: Text;           # reference to the container running the tfchain
    node @1: Text;                # reference to the node running the tfchain container
    rpcPort @2: UInt32=23112;     # rpc port of tfchain daemon
    apiPort @3: UInt32=23110;     # http port for tfchain client
    walletSeed @4: Text;
    walletPassphrase @5: Text;
    nodeMountPoint @6: Text; # the node mountpoint that will be mounted at containerMountPoint
    containerMountPoint @7: Text; # the container destination where hostMountPoint will be mounted
    walletAddr @8: Text; # address of the wallet
}
