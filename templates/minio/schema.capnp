@0x9895a7c4a0b2bd61;


struct Schema {
    zerodbs @0: List(Text); # list of zerodbs endpoints used as backend for minio ex: ['192.168.122.87:9600']
    namespace @1: Text; # namespace to use on the 0-db
    nsSecret @2: Text; # secret to use to have access to the namespace on the 0-db servers
    login @3: Text; # minio login. End user needs to know this login to have access to minio
    password @4: Text; #minio password. End user needs to know this login to have access to minio
    privateKey @5: Text; # encryption private key
    metaPrivateKey @6: Text; # metadata encryption private key
    dataShard @7: UInt32=1;
    parityShard @8: UInt32=0;
    tlog @9: Tlog;

    struct Tlog {
        namespace @0 :Text; # name of the tlog namespace
        address @1 :Text; # ip:port of the tlog namespace
    }
}