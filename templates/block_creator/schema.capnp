@0xef6962ec95fcaa33;

struct Schema {
    container @0: Text; # reference to the container running the tfchain
    node @1: Text;      # reference to the node running the tfchain container
    rpcAddr @2: Text;   # rpc address of tfchain daemon
    apiAddr @3: Text;   # http address of tfchain client
}
