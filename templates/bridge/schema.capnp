@0xcbee028f0e7bab9f;

struct Schema {
    HWAddr @0: Text; # MAC address of the bridge. If none, a one will be created for u
    Mode @1: Mode; # Networking mode, options are none, static, and dnsmasq
    Nat @2: Bool; # If true, SNAT will be enabled on this bridge. (IF and ONLY IF an IP is set on the bridge via the settings, otherwise flag will be ignored) (the cidr attribute of either static, or dnsmasq modes)
    Settings: Settings;

    enum Mode{
        none @0;
        static @1;
        dnsmasq @2;
    }

    enum Settings {
        StaticSetting @1;
        DNSMasqSetting @2;
    }

    struct StaticSetting {
        CIDR @0 :Text; # bridge will get assigned the given IP address (ip/net)
    }

    struct DNSMasqSetting {
        # bridge will get assigned the ip in cidr
        # and each running container that is attached to this IP will get
        # IP from the start/end range. Netmask of the range is the netmask
        # part of the provided cidr.
        # if nat is true, SNAT rules will be automatically added in the firewall.
        CIDR @0 :Text;
        Start @1 :Uint32;
        End @2 :Uint32;
    }
}
