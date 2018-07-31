@0x9ace40199f22c00a;

struct Schema {
    instanceName @0: Text; #Name of the instance
    host @1: Text; #the host name e.g 'localhost'
    port @2: Text;  #port of the influxdb client, by default 8086
    login @3: Text; #username by default root
    passwd @4: Text; #password by default root
    ssl @5: Bool; #Use HTTPS for requests by default false
    verifySsl @6 : Bool; #Verify that HTTPS is working by connecting to InfluxDB  by default false

}