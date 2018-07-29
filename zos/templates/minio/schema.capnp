@0x9895a7c4a0b2bd61;


struct Schema {
    zerodbs @0: List(Text); # list of zerodbs endpoints used as backend for minio ex: ['192.168.122.87:9600']
    namespace @1: Text; # namespace to use on the 0-db
    nsSecret @2: Text; # secret to use to have access to the namespace on the 0-db servers
    login @3: Text; # minio login. End user needs to know this login to have access to minio
    password @4: Text; #minio password. End user needs to know this login to have access to minio
    listenPort @5: UInt32=9000; # the port to bind to
    resticRepo @6: Text="s3:http://195.134.212.42/"; # restic repo to use for metadata backup
    resticRepoPassword @7: Text; # restic repo password
    resticUsername @8: Text="zaibon"; # rustic username
    resticPassword @9: Text="coucou01"; # rustic password
    privateKey @10: Text; # encryption private key
    metaPrivateKey @11: Text; # metadata encryption private key
}