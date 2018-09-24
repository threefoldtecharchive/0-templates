@0xb6532701946c636f;


struct Schema {
   listenPeerUrls @0: List(Text); # List of URLs to listen on for peer traffic default: "http://localhost:2380"
   listenClientUrls @1: List(Text); # List of URLs to listen on for client traffic default: "http://localhost:2379"
   initialAdvertisePeerUrls @2: List(Text); # List of this member's peer URLs to advertise to the rest of the cluster. default: "http://localhost:2380"
   advertiseClientUrls @3: List(Text); # List of this member's client URLs to advertise to the rest of the cluster default: "http://localhost:2379"
   clientPort @4: UInt32=2379;
   peerPort @5: UInt32=2380;
}
