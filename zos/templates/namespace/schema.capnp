@0xbec2e1d1f82225f1;


struct Schema {
    size @0: Int32; # size of the namespace
    diskType @1 :DiskType; # type of disk to use for this namespace
    mode @2 :Mode; # zero-db mode
    public @3 :Bool; # see https://github.com/rivine/0-db#nsset for detail about public mode
    password @4: Text; # password of the namespace. if empty it will be generated automatically
    zerodb @5 :Text; # instance name of the zerodb where the namespace is deployed. User don't have to fill this attribute
    nsName @6 :Text;

    enum DiskType{
        hdd @0;
        ssd @1;
    }

    enum Mode { # see https://github.com/rivine/0-db#running-modes for detail about the different modes
        user @0;
        direct @1;
        seq @2;
    }
}
