@0xcd4c6fb7346ea294;


struct Schema {
    size @0 :Int32; # size of the vdisk and namespace
    diskType @1 :DiskType; # type of disk to use for the namespace
    mountPoint @2 :Text;
    filesystem @3 :Text;
    namespace @4 :Text; # instance name of the zerodb where the namespace is deployed. User doesn't have to fill this attribute.
    nsName @5 :Text; # name of the namespace to be created on zerodb. User doesn't have to fill this attribute.
    label @6 :Text; # label to be used for the disk on any vm

    enum DiskType{
        hdd @0;
        ssd @1;
    }
}
