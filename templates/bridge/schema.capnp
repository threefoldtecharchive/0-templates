@0xcbee028f0e7bab9f;

struct Schema {
    hwaddr @0: Text; # MAC address of the bridge. If none, a one will be created for u
    mode @1: Mode; # Networking mode, options are none, static, and dnsmasq
    nat @2: Bool=false; # If true, SNAT will be enabled on this bridge. (IF and ONLY IF an IP is set on the bridge via the settings, otherwise flag will be ignored) (the cidr attribute of either static, or dnsmasq modes)
    settings @3: Setting;

    enum Mode{
        none @0;
        static @1;
        dnsmasq @2;
    }


    struct Setting {
        # bridge will get assigned the ip in cidr
        # and each running container that is attached to this IP will get
        # IP from the start/end range. Netmask of the range is the netmask
        # part of the provided cidr.
        # if nat is true, SNAT rules will be automatically added in the firewall.
        cidr @0: Text;
        start @1: Int32;
        end @2: Int32;
    }
}
