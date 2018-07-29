@0xe51c667eb60edfed;

struct Schema {
    username @0: Text; # Racktivity username
    password @1: Text; # Racktivity password
    host @2: Text; # Target host address
    port @3: UInt32=80; # Target port
}
