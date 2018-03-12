@0x8c4ee3b29d3ae54d;

struct Schema {
    container @0: Text;           # reference to the container running the tfchain
    node @1: Text;                # reference to the node running the tfchain container
    rpcPort @2: UInt32=23112;     # rpc port of tfchain daemon
    apiPort @3: UInt32=23110;     # http port for tfchain client
    nodeMountPoint @4: Text;      # the node mountpoint that will be mounted at containerMountPoint
    containerMountPoint @5: Text; # the container destination where hostMountPoint will be mounted
    walletSeed @6: Text;
    walletPassphrase @7: Text;
}
