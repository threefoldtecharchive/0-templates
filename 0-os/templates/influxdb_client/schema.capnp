@0x9ace40199f22c00a;

struct Schema {
    host @0: Text; #the host name e.g 'localhost'
    port @1: Text;  #port of the influxdb client, by default 8086
    login @2: Text; #username by default root
    passwd @3: Text; #password by default root
    ssl @4: Bool; #Use HTTPS for requests by default false
    verifySsl @5 : Bool; #Verify that HTTPS is working by connecting to InfluxDB  by default false

}