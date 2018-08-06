from jumpscale import j
import argparse, random, time, os

def main(options):
    """Setup testing environment using Zero-Boot client
    
    Arguments:
        options {object} -- argparse option object
            router_address {str} -- address of the router in the zerotier network.
            router_username {str} -- username of the router.
            router_password {str} -- password of the router.
            zerotier_network {str} -- router's zerotier network.
            zerotier_token {str} -- router's zerotier token.
            rack_hostname {str} -- address of the racktivity device in the internal router network.
            rack_username {str} -- username of the racktivity device.
            rack_password {str} -- password of the racktivity device.
            rack_module_id {str} -- rack module id.
            cpu_hostname {str} -- cpu's hostname.
            cpu_rack_port {int} -- cpu's rack port.
            core_0_branch {str} -- core-0 branch.
    """

    instance_name = 'test-{}'.format(random.randint(1, 1000))
    
    # configure ssh client
    ssh_data = {
        'addr':options.router_address,
        'login':options.router_username,
        'passwd_':options.router_password
    }
    sshclient = j.clients.ssh.get(instance_name, data=ssh_data)

    #zerotier client
    zerotier_data = {
        'token_':options.zerotier_token
    }
    zerotier = j.clients.zerotier.get(instance_name, data=zerotier_data)

    # rack client
    rack_data = {
        'hostname':options.rack_hostname,
        'username':options.rack_username,
        'password_':options.rack_password
    }
    rack = j.clients.racktivity.get(instance_name, data=rack_data)

    # zboot client
    zboot_data = {
        'network_id':options.zerotier_network,
        'sshclient_instance':instance_name,
        'zerotier_instance':instance_name
    }
    zboot = j.clients.zboot.get(instance_name, data=zboot_data)

    print("[*] Create testing zerotier")
    testing_zt_network = zerotier.network_create(public=False, subnet='10.147.19.0/24')
    
    print("[*] Set ipxe boot url")    
    networks = zboot.networks.get()
    host = networks.hosts.get(options.cpu_hostname)

    ipxe_boot_url = 'http://unsecure.bootstrap.gig.tech/ipxe/{branch}/{zerotier}/development'.format(
        branch=options.core_0_branch,
        zerotier=testing_zt_network.id
    )

    host.configure_ipxe_boot(ipxe_boot_url)

    print("[*] Reboot node %s" % (options.cpu_hostname))    
    zboot.port_power_cycle([options.cpu_rack_port], rack, options.rack_module_id)

    for _ in range(60):
        members = testing_zt_network.members_list()
        if members:
            members[0].authorize()
            break
        else:
            time.sleep(10)
    else:
        raise RuntimeError("Node doesn't join the zerotier network")
    
    time.sleep(60)
    
    members = testing_zt_network.members_list()
    cpu_zt_ip = members[0].data['config']['ipAssignments'][0]

    print("[*] Done")
    print("[*] Zerotier network %s" % (testing_zt_network.id))
    print("[*] Node zerotier ip %s" % (cpu_zt_ip))

    os.system('printf "{}" > /tmp/testing_zt_network.txt'.format(testing_zt_network.id))
    os.system('printf "{}" > /tmp/cpu_zt_ip.txt'.format(cpu_zt_ip))
    
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--router_address", type=str, required=True, help="address of the router in the zerotier network")
    parser.add_argument("--router_username", type=str, required=True, help="username on the router")
    parser.add_argument("--router_password", type=str, required=True, help="password of router username")
    parser.add_argument("--zerotier_network", type=str, required=True, help="zerotier network of the router")
    parser.add_argument("--zerotier_token", type=str, required=True, help="zerotier token")
    parser.add_argument("--rack_hostname", type=str, required=True, help="address of the racktivity device in the internal router network")
    parser.add_argument("--rack_username", type=str, required=True, help="user login for the racktivity device")
    parser.add_argument("--rack_password", type=str, required=True, help="password for rack device")
    parser.add_argument("--rack_module_id", type=str, required=True, help="racktivity device model id")
    parser.add_argument("--core_0_branch", type=str, required=True, help="zero-os branch")
    parser.add_argument("--cpu_hostname", type=str, required=True, help="cpu hostname")
    parser.add_argument("--cpu_rack_port", type=int, required=True, help="racktivity device port connected to the target node")
      
    options = parser.parse_args()
    main(options)