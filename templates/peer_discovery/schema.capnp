@0xba1805e2bd8cb67b;

struct Schema {
    # reference to the node running the tfchain container
    node @0: Text;

    # container name
    containerName @1: Text;

     # rpc port of tfchain daemon
    rpcPort @2: UInt32=23112;

    # http port for tfchain client
    apiPort @3: UInt32=23110;

    # interval between peer discovery in sec
    interval @4: UInt32=43200;
}