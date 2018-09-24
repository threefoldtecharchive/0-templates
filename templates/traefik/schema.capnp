@0xb1e322af4c1787e4;

struct Schema {
    etcdServerName @0: Text; #Name of Etcd service
    etcdWatch @1: Bool=true; #watch changes in Traefik web 
    nodePort @2: Int32=9700; # the port to bind to
}
