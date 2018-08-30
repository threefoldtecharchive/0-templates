@0xce573a7ce53b89d1;

struct Schema {
    # url pointing to the 0-db to use to store the robot data
    # supported format is : `zdb://admin_passwd:encryption_key@hostname:port/namespace`
    dataRepo @0: Text;
}
