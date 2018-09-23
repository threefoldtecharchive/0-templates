@0xaf3b04a861b5a7f1;

struct Schema {
    etcdServerName @0: Text; #Name of Etcd service
    upsteram @1 : Text; #by default 8.8.8.8:53 8.8.4.4:53
    domain @2 : Text;
}