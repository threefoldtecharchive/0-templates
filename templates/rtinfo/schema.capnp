@0x9e6c1e6c6116f99b;

struct Schema {
    address @0: Text; # rtinfod address
    port @1: UInt16 = 9930; # rtinfod listening client port
    disks @2: List(Text) = [""]; # List of prefixes of disks to filter on, default returns rtinfo of all disks to rtinfod
}
