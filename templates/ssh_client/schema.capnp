@0xc1890c8a0387edda;

struct Schema {
    host @0: Text; # Target host address
    port @1: UInt16=22; # Target port
    login @2: Text; # username/login
    password @3: Text; # password
}
