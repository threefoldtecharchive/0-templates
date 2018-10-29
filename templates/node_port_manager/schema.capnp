@0xce37e3f2d23d7dcc;

struct Schema {
    ports @0 :List(Port);

    struct Port {
        port @0 :Int32;
        serviceGuid @1 :Text;
    }
}