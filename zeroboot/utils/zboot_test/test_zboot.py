import sys
import time
import os
import traceback

from js9 import j

WIPE=False      # wipe all drives during cleanup
WIPE_KEY=True   # wipe ssh key used for connecting to the VM
SHUTDOWN=False  # shutdown host at cleanup
SHUTDOWN_VM=False # send shutdown action after VM was confirmed up and running
MAX_RETRIES = 10 # max amount of pings/alive checks

ROBOT_INSTANCE = "zboot-robot1"
ZEROBOOT_POOL = 'pool-1'
MAX_RESERVATIONS_PER_RUN = 10
BOOT_URL = "https://bootstrap.gig.tech/krn/master/0/development"

VM_SSH_KEY_PATH = "/tmp/zboot_testkey" # Where to store generated key to use in test (pub key will be copied into vm so we can ssh to it)
VM_SSH_PORT = 2222
VM_DATA = {
    'name': 'Ubuntu-VM',
    'cpu': 1,
    'memory': 256,
    'disks': [{'name': 'disk1', 'mountPoint': '/opt/storage'}],
    'flist':'https://hub.gig.tech/gig-bootable/ubuntu:16.04.flist',
    'nics': [{'type':'default', 'name': 'default_nic'}],
    'ports': [{'source': VM_SSH_PORT, 'target': 22, 'name': 'ssh'}],
    'configs': [],
}

reservation_pool = []
host_pool = []

def main(argv):
    key = j.clients.sshkey.key_generate(VM_SSH_KEY_PATH, load=True)
    try:

        VM_DATA['configs'].append({'path': '/root/.ssh/authorized_keys', 'content': key.pubkey, 'name': 'sshkey'})

        i = 1
        while run(i, key):
            print("\nRun %s completed\n" % str(i))
            i += 1

        print("Test should have completed successfully now")

    except (BaseException, KeyboardInterrupt) as err:
        print("Something went wrong:")
        traceback.print_exc()
        print(str(err) + "\n\n")

    finally:
        if WIPE_KEY:
            key.delete()
        cleanup()

        print("Done!")

def run(run_nr, key):
    """ Single run of booting up and starting up to MAX_RESERVATIONS_PER_RUN
    if MAX_RESERVATIONS_PER_RUN True is returned, else False is returned
    """
    max_res_reached=False
    reservations = []
    hosts = []

    # connect to zboot manager robot
    robot = j.clients.zrobot.robots[ROBOT_INSTANCE]

    # reserve all the nodes
    print("Reserving hosts")

    reservation_data = {
        'zerobootPool': ZEROBOOT_POOL,
        'lkrnUrl': BOOT_URL,
    }
    i = 0
    while True:
        r = robot.services.create(
            "github.com/zero-os/0-boot-templates/zeroboot_reservation/0.0.1",
            "test_reservation-%s-%s" % (str(run_nr), str(i)),
            data=reservation_data
        )
        # reserve and boot with lastest zero-os image
        try:
            r.schedule_action('install').wait(die=True)
        except BaseException as err:
            if not "no free hosts available" in str(err).lower():
                raise(err)
            print("No hosts left to reserve")
            r.delete()
            break

        hostname = r.schedule_action('host').wait(die=True).result
        ip = r.schedule_action('ip').wait(die=True).result
        zos_client = j.clients.zos.get(
            instance=hostname,
            data={
                "host": ip,
                "port": 6379,
            }
        )
        host = j.clients.zos.sal.get_node(instance=hostname)

        print("reserved host: %s" % hostname)
        hosts.append({'name': hostname, 'host':host, 'ip':ip})
        reservations.append(r)
        # immediately add to pool so they can be cleaned up if something goes wrong
        host_pool.append({'name': hostname, 'host':host, 'ip':ip})
        reservation_pool.append(r)

        i += 1
        if i >= MAX_RESERVATIONS_PER_RUN:
            max_res_reached = True
            break

    print("\n%s hosts reserved\n" % str(len(reservations)))

    # Ping each host
    for h in hosts:
        print("Pinging host: %s" % h['name'])
        retry = 1
        while not h['host'].is_running():
            print("ping attempt %s..." % str(retry))
            retry += 1
            if retry > MAX_RETRIES:
                raise RuntimeError('Maximum retries of connecting to host reached')
            print("Waiting before next ping")
            time.sleep(30)

        print("\n%s\n" % h['host'].client.ping())

    # Create VM in each host
    i = 1
    for h in hosts:
        # create robot client
        j.clients.zrobot.new("test-host-robot", data={'url':'http://%s:6600' % (h['ip'])})
        host_robot = j.clients.zrobot.robots['test-host-robot']

        # check host robot is alive
        retry = 1
        while True:
            print("robot ping attempt %s for host %s..." % (str(retry), h['name']))

            try:
                host_robot.templates.uids
                print("Host %s's robot is ready" % h['name'])
                break
            except BaseException:
                retry += 1
                if retry > MAX_RETRIES:
                    raise RuntimeError('Maximum retries of connecting to host robot reached')
                print("Waiting before next robot ping")
                time.sleep(10)

        # create vm service
        # delete before creating if already exists
        for s in host_robot.services.find(name=VM_DATA["name"]):
            print('cleaning up VM on host %s' % h['name'])
            s.schedule_action('uninstall').wait(die=True)
            s.delete()

        print("Creating VM on host %s using the robot" % h['name'])
        data={
            'cpu': VM_DATA['cpu'],
            'memory': VM_DATA['memory'],
            'flist': VM_DATA['flist'],
            'nics': VM_DATA['nics'],
            'ports': VM_DATA['ports'],
            'configs': VM_DATA['configs'],
        }
        vm_service = host_robot.services.create("github.com/zero-os/0-templates/vm/0.0.1", VM_DATA["name"], data=data)
        vm_service.schedule_action("install").wait(die=True)

        # proof it's available
        # get ubuntu version over ssh connection
        ssh_service = j.clients.ssh.get('zboot-ssh', data={'sshkey': key.config.instance, 'addr': h['ip'], 'port': VM_SSH_PORT})
        # wait for ssh port to come alive
        retry = 1
        while True:
            try:
                ssh_service.connect()
                print('SSH connection to container established')
                break
            except BaseException:
                retry += 1
                if retry > MAX_RETRIES:
                    raise RuntimeError('Maximum retries of connecting to container reached')
                print("Waiting before next ssh ping")
                time.sleep(10)
    
        pf = ssh_service.prefab

        # execute `lsb_release -a` over prefab
        _, out, _ = pf.bash.executor.execute('lsb_release -a')
        print("\nVM OS release:\n%s\n" % out)

        if SHUTDOWN_VM:
            vm_service.schedule_action("uninstall").wait(die=True)
            vm_service.delete()

        print("----")
    
    return max_res_reached

def cleanup():
    print("\nCleaning up...")
    # cleanup clients
    for h in host_pool:
        if WIPE:
            try:
                for d in h['host'].disks.list():
                    h['host'].client.system('dd if=/dev/zero of=%s bs=1G count=1' % d.devicename).get()
            except BaseException as err:
                print('Something went wrong wiping the disks for host %s : %s' % (h['name'], err))

        j.clients.zos.delete(instance=h['name'])

    for r in reservation_pool:
        if SHUTDOWN:
            r.schedule_action('uninstall').wait(die=True)
        r.delete()

if __name__ == "__main__":
    main(sys.argv)
