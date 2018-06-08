@0xd27d62a90a1cc621;

struct Schema {
    # reference to the node running the tfchain container (required).
    node @0: Text;

    # container name (required).
    container @1: Text;

     # rpc port of tfchain daemon.
    rpcPort @2: UInt32=23112;

    # http port for tfchain client.
    apiPort @3: UInt32=23110;

    # interval between scanning network for new peers. Default to 24 hours.
    intervalScanNetwork @4: UInt32=86400;

    # interval between adding new peers in seconds. Default to 30 min.
    intervalAddPeer @5: UInt32=1800;

    # list of discovered peers (autofilled).
    discoveredPeers @6: List(Text);
}