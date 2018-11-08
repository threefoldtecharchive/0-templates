@0xc56f053f8caf5755;

struct Schema {
    webGateway @0 :Text; # web_gateway service to use for etcd connections
    domain @1 :Text; # Reverse proxy domain
    servers @2 :List(Text); # List of backend servers to expose
}