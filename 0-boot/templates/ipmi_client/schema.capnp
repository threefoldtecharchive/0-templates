@0xba5ceb8a44564b39;

struct Schema {
    bmc @0: Text; # bmc host address
    user @1: Text; # ipmi login username
    password @2: Text; # ipmi password
    port @3: UInt32=623; # ipmi port
}
