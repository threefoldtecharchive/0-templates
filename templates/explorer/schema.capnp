@0x8081fe890abc33e1;

struct Schema {
    container @0: Text; # reference to the container running the explorer
    node @1: Text;      # reference to the node running the explorer container
    rpcAddr @2: Text;   # rpc address of explorer daemon
}
