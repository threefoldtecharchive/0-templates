@0xcb009910491c0ba6; 


struct Schema {
    host @0: Text; # redis address for the client
    port @1 :UInt32 = 6379; # redis port for client
    password @2: Text; # redis password
    ssl @3: Bool; # enable/disable redis ssl
    db @4: UInt32 = 0; # redis db number
    timeout @5: UInt32 = 120; # redis socket timeout
    unixSocket @6: Text; # unix socket path
}
