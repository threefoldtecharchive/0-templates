import sys
import csv
from argparse import ArgumentParser

from js9 import j

def main(argv):
    parser = ArgumentParser()
    parser.add_argument("-d", "--data", dest="data_file", help="CSV file to read the host data from", required=True)
    parser.add_argument("-r", "--robot", dest="robot_name", help="0-robot instance to use", required=True)
    parser.add_argument("-p", "--pool", dest="pool_name", help="Puts all hosts in a pool with provided name", required=False)
    parser.add_argument("-c", "--clean", dest="clean", help="Start from clean env. Deletes all reservation, pool, racktivity host, racktivity client, zeroboot and ssh services from the robot it has access to.", required=False, action='store_true', default=False)

    args = parser.parse_args()

    if args.robot_name == "debug":
        from unittest.mock import MagicMock
        robot = MagicMock()
    else:
        robot = j.clients.zrobot.robots[args.robot_name]

    if args.clean:
        clean_env(robot)

    create_ssh_services(robot, args.data_file)
    create_zboot_services(robot, args.data_file)
    create_rack_services(robot, args.data_file)
    create_ipmi_services(robot, args.data_file)

    hosts = []
    hosts.extend(create_rack_host_services(robot, args.data_file))
    hosts.extend(create_ipmi_host_services(robot, args.data_file))

    if args.pool_name:
        add_hosts_pool_service(robot, hosts, args.pool_name)

def clean_env(robot):
    """ Cleans up environment of services from the following templates:

        - Uninstalls and deletes the zeroboot_reservation templates
        - Deletes pool services
        - Deletes racktivity host services
        - Deletes racktivity client services
        - Deletes zeroboot client services
        - Deletes ssh client services

    Keep in mind, this will only remove the services the zero-robot client has access to

    Arguments:
        robot {ZRobot} -- Robot instance
    
    """
    print("Cleaning up environment...")

    # delete reservation services
    for s in robot.services.find(template_uid='github.com/zero-os/0-boot-templates/zeroboot_reservation/0.0.1'):
        s.schedule_action("uninstall").wait(die=True).result
        s.delete()

    # delete pool services
    for s in robot.services.find(template_uid='github.com/zero-os/0-boot-templates/zeroboot_pool/0.0.1'):
        s.delete()

    # delete racktivity host services
    for s in robot.services.find(template_uid='github.com/zero-os/0-boot-templates/zeroboot_racktivity_host/0.0.1'):
        s.delete()

    # delete racktivity client services        
    for s in robot.services.find(template_uid='github.com/zero-os/0-boot-templates/racktivity_client/0.0.1'):
        s.delete()

    # delete zboot services
    for s in robot.services.find(template_uid='github.com/zero-os/0-boot-templates/zeroboot_client/0.0.1'):
        s.delete()

    # delete ssh services
    for s in robot.services.find(template_uid='github.com/zero-os/0-boot-templates/ssh_client/0.0.1'):
        s.delete()

    print("Environment should be cleaned up now!")

def create_ssh_services(robot, data_file):
    """Creates the SSH clients defined in the CSV file
    
    Arguments:
        robot {ZRobot} -- Robot instance
        data_file {str} -- location of the CSV file
    """
    with open(data_file, newline='') as csvfile:
        rdr = csv.reader(csvfile, delimiter=',')
        data_found = False
        title_indexes = {}
        row_i = -1
        for row in rdr:
            row_i += 1
            # find ssh data starting row
            if not data_found:
                if str(row[0]).lower() == ('ssh_data'):
                    print("ssh_data header found at row %s" % str(row_i + 1))
                    data_found = True
                continue
            
            # the column titles should be in  the next row
            if not title_indexes:
                col_i = 0
                for col in row:
                    if col.lower() == 'host_address':
                        title_indexes['host_address'] = col_i
                    if col.lower() == 'hostname':
                        title_indexes['hostname'] = col_i
                    if col.lower() == 'user':
                        title_indexes['user'] = col_i
                    if col.lower() == 'password':
                        title_indexes['password'] = col_i
                    if col.lower() == 'port':
                        title_indexes['port'] = col_i

                    col_i += 1
                
                # check required columns
                for item in ('host_address', 'user', 'password', 'hostname'):
                    try:
                        title_indexes[item]
                    except KeyError:
                        raise RuntimeError("key '%s' was not provided for the ssh_data at row %s" % (item, str(row_i + 1)))
                
                continue

            # keep adding services till empty row or EOF
            if row[0] in (None, "") and row[1] in (None, ""):
                print('SSH client data ended at row %s' % str(row_i + 1))
                break

            # create ssh client
            data={}
            data["login"] = row[title_indexes['user']]
            data["password"] = row[title_indexes['password']]
            data["host"] = row[title_indexes['host_address']]
            if title_indexes.get("port") and row[title_indexes["port"]]:
                data["port"] = int(row[title_indexes["port"]])

            robot.services.find_or_create(
                "github.com/zero-os/0-boot-templates/ssh_client/0.0.1",
                row[title_indexes["hostname"]],
                data=data,
            )
        else:
            if not data_found:
                print("No SSH client data was found")
            else:
                print("SSH client data ended at last row")

def create_zboot_services(robot, data_file):
    """Creates the zboot clients services defined in the CSV file
    
    Arguments:
        robot {ZRobot} -- Robot instance
        data_file {str} -- location of the CSV file
    """
    with open(data_file, newline='') as csvfile:
        rdr = csv.reader(csvfile, delimiter=',')
        data_found = False
        title_indexes = {}
        row_i = -1
        for row in rdr:
            row_i += 1
            # find zboot data starting row
            if not data_found:
                if str(row[0]).lower() == ('zboot_data'):
                    print("zboot_data header found at row %s" % str(row_i + 1))
                    data_found = True
                continue
            
            # the column titles should be in  the next row
            if not title_indexes:
                col_i = 0
                for col in row:
                    if col.lower() == 'name':
                        title_indexes['name'] = col_i
                    if col.lower() == 'ztier_network':
                        title_indexes['ztier_network'] = col_i
                    if col.lower() == 'ssh_service':
                        title_indexes['ssh_service'] = col_i
                    if col.lower() == 'ztier_service':
                        title_indexes['ztier_service'] = col_i

                    col_i += 1
                
                # check required columns
                for item in ('name', 'ztier_network', 'ssh_service'):
                    try:
                        title_indexes[item]
                    except KeyError:
                        raise RuntimeError("key '%s' was not provided for the zboot_data at row %s" % (item, str(row_i + 1)))
                
                continue

            # keep adding services till empty row or EOF
            if row[0] in (None, "") and row[1] in (None, ""):
                print('Zboot client data ended at row %s' % str(row_i + 1))
                break

            # create ssh client
            data={}
            data["networkId"] = row[title_indexes['ztier_network']]
            data["sshClient"] = row[title_indexes['ssh_service']]
            if title_indexes.get("ztier_service") and row[title_indexes["ztier_service"]]:
                data["zerotierClient"] = int(row[title_indexes["ztier_service"]])

            robot.services.find_or_create(
                "github.com/zero-os/0-boot-templates/zeroboot_client/0.0.1",
                row[title_indexes["name"]],
                data=data,
            )
        else:
            if not data_found:
                print("No Zboot client data was found")
            else:
                print("Zboot client data ended at last row")

def create_rack_services(robot, data_file):
    """Creates the racktivity clients defined in the CSV file
    
    Arguments:
        robot {ZRobot} -- Robot instance
        data_file {str} -- location of the CSV file
    """
    with open(data_file, newline='') as csvfile:
        rdr = csv.reader(csvfile, delimiter=',')
        rack_data_found = False
        title_indexes = {}
        row_i = -1
        for row in rdr:
            row_i += 1
            # find racktivity data starting row
            if not rack_data_found:
                if str(row[0]).lower() == ('racktivity_data'):
                    print("racktivity_data header found at row %s" % str(row_i + 1))
                    rack_data_found = True
                continue

            # the column titles should be in  the next row
            if not title_indexes:
                col_i = 0
                for col in row:
                    if col.lower() == 'host_address':
                        title_indexes['host_address'] = col_i
                    if col.lower() == 'user':
                        title_indexes['user'] = col_i
                    if col.lower() == 'password':
                        title_indexes['password'] = col_i
                    if col.lower() == 'hostname':
                        title_indexes['hostname'] = col_i
                    if col.lower() == 'port':
                        title_indexes['port'] = col_i
                    col_i += 1
                
                # check required columns
                for item in ('host_address', 'user', 'password', 'hostname'):
                    try:
                        title_indexes[item]
                    except KeyError:
                        raise RuntimeError("key '%s' was not provided for the racktivity_data at row %s" % (item, str(row_i + 1)))
                
                continue

            # keep adding racktivity hosts till empty row or EOF
            if row[0] in (None, "") and row[1] in (None, ""):
                print('Racktivity client data ended at row %s' % str(row_i + 1))
                break

            # create racktivity client
            data={}
            data["username"] = row[title_indexes['user']]
            data["password"] = row[title_indexes['password']]
            data["host"] = row[title_indexes['host_address']]
            if title_indexes.get("port") and row[title_indexes["port"]]:
                data["port"] = int(row[title_indexes["port"]])

            robot.services.find_or_create(
                "github.com/zero-os/0-boot-templates/racktivity_client/0.0.1",
                row[title_indexes["hostname"]],
                data=data,
            )
        else:
            if not rack_data_found:
                print("No racktivity client data was found")
            else:
                print("Racktivity client data ended at last row")

def create_rack_host_services(robot, data_file):
    """Creates the racktivity host services
    
    Arguments:
        robot {ZRobot} -- Robot instance
        data_file {str} -- Location of CSV file

    Returns:
        [str] -- List of host service names created
    """
    hosts = []

    with open(data_file, newline='') as csvfile:
        rdr = csv.reader(csvfile, delimiter=',')
        host_data_found = False
        title_indexes = {}
        row_i = -1
        for row in rdr:
            row_i += 1
            # find host data starting row
            if not host_data_found:
                if str(row[0]).lower() == ('rack_host_data'):
                    print("rack_host_data header found at row %s" % str(row_i + 1))
                    host_data_found = True
                continue

            # the column titles should be in the next row
            if not title_indexes:
                col_i = 0
                for col in row:
                    if col.lower() == 'zboot_service':
                        title_indexes['zboot_service'] = col_i
                    if col.lower() == 'racktivity_data':
                        title_indexes['racktivity_data'] = col_i
                    if col.lower() == 'redundant_racktivity_data':
                        title_indexes['redundant_racktivity_data'] = col_i
                    if col.lower() == 'mac':
                        title_indexes['mac'] = col_i
                    if col.lower() == 'ip':
                        title_indexes['ip'] = col_i
                    if col.lower() == 'network':
                        title_indexes['network'] = col_i
                    if col.lower() == 'hostname':
                        title_indexes['hostname'] = col_i
                    if col.lower() == 'lkrn_url':
                        title_indexes['lkrn_url'] = col_i
                    col_i += 1
                
                # check required columns
                for item in ('zboot_service', 'racktivity_data', 'mac', 'ip', 'network', 'lkrn_url'):
                    try:
                        title_indexes[item]
                    except KeyError:
                        raise RuntimeError("key '%s' was not provided for the rack_host_data at row %s" % (item, str(row_i + 1)))

                continue
            
            # keep adding racktivity hosts till empty row or EOF
            if row[0] in (None, "") and row[1] in (None, ""):
                print('Host data ended at row %s' % str(row_i + 1))
                break

            # if service already exists, skip
            s = robot.services.find(name=row[title_indexes['hostname']])
            if len(s) > 0:
                print("There is already a service running for host %s. Skipping to next host" % row[title_indexes['hostname']])
                continue

            data = {}
            data["zerobootClient"] = row[title_indexes['zboot_service']]
            data["mac"] = row[title_indexes['mac']].lower()
            data["ip"] = row[title_indexes['ip']]
            data["hostname"] = row[title_indexes['hostname']]
            data["network"] = row[title_indexes['network']]
            data["lkrn_url"] = row[title_indexes['lkrn_url']]

            data['racktivities'] = []
            data['racktivities'].append(_rack_data_conv(row[title_indexes['racktivity_data']]))

            if title_indexes.get("redundant_racktivity_data") and row[title_indexes["redundant_racktivity_data"]]:
                data['racktivities'].append(_rack_data_conv(row[title_indexes['redundant_racktivity_data']]))


            host_service = robot.services.create(
                "github.com/zero-os/0-boot-templates/zeroboot_racktivity_host/0.0.1",
                data["hostname"],
                data=data,
            )
            host_service.schedule_action('install').wait(die=True)

            hosts.append(data["hostname"])

        else:
            if not host_data_found:
                print("No host data was found")
            else:
                print("host data ended at last row")

    return hosts

def _rack_data_conv(data):
    """ Converts data in CSV file to dict

    input format:
    "<client>;<port>;<powermodule>" Where the powermodule is optional

    output format:
    {
        'client': <client>,
        'port': <port>,
        'powermodule': <powermodule>,
    }
    
    Arguments:
        data str -- data in the CSV field
    
    Returns:
        dict -- data in dict form
    """
    result = {}

    x = data.split(";")

    if len(x) == 2:
        x.append(None)
    elif len(x) < 2:
        raise RuntimeError("Not enough segments in racktivity data. Found: %s" % data)
    elif len(x) > 3:
        raise RuntimeError("too many segments in racktivity data. Found: %s" % data)

    result['client'] = x[0]
    result['port'] = int(x[1])
    result['powermodule'] = x[2]

    return result

def create_ipmi_services(robot, data_file):
    """Creates the ipmi clients defined in the CSV file
    
    Arguments:
        robot {ZRobot} -- Robot instance
        data_file {str} -- location of the CSV file
    """
    with open(data_file, newline='') as csvfile:
        rdr = csv.reader(csvfile, delimiter=',')
        ipmi_data_found = False
        title_indexes = {}
        row_i = -1
        for row in rdr:
            row_i += 1
            # find ipmi data starting row
            if not ipmi_data_found:
                if str(row[0]).lower() == ('ipmi_data'):
                    print("ipmi_data header found at row %s" % str(row_i + 1))
                    ipmi_data_found = True
                continue

            # the column titles should be in  the next row
            if not title_indexes:
                col_i = 0
                for col in row:
                    if col.lower() == 'host_address':
                        title_indexes['host_address'] = col_i
                    if col.lower() == 'user':
                        title_indexes['user'] = col_i
                    if col.lower() == 'password':
                        title_indexes['password'] = col_i
                    if col.lower() == 'hostname':
                        title_indexes['hostname'] = col_i
                    if col.lower() == 'port':
                        title_indexes['port'] = col_i
                    col_i += 1
                
                # check required columns
                for item in ('host_address', 'user', 'password', 'hostname'):
                    try:
                        title_indexes[item]
                    except KeyError:
                        raise RuntimeError("key '%s' was not provided for the ipmi_data at row %s" % (item, str(row_i + 1)))
                
                continue

            # keep adding ipmi services till empty row or EOF
            if row[0] in (None, "") and row[1] in (None, ""):
                print('IPMI client data ended at row %s' % str(row_i + 1))
                break

            # create ipmi client
            data={}
            data["username"] = row[title_indexes['user']]
            data["password"] = row[title_indexes['password']]
            data["host"] = row[title_indexes['host_address']]
            if title_indexes.get("port") and row[title_indexes["port"]]:
                data["port"] = int(row[title_indexes["port"]])

            robot.services.find_or_create(
                "github.com/zero-os/0-boot-templates/ipmi_client/0.0.1",
                row[title_indexes["hostname"]],
                data=data,
            )
        else:
            if not ipmi_data_found:
                print("No ipmi client data was found")
            else:
                print("IPMI client data ended at last row")

def create_ipmi_host_services(robot, data_file):
    """Creates the ipmi host services
    
    Arguments:
        robot {ZRobot} -- Robot instance
        data_file {str} -- Location of CSV file

    Returns:
        [str] -- List of host service names created
    """
    hosts = []

    with open(data_file, newline='') as csvfile:
        rdr = csv.reader(csvfile, delimiter=',')
        host_data_found = False
        title_indexes = {}
        row_i = -1
        for row in rdr:
            row_i += 1
            # find host data starting row
            if not host_data_found:
                if str(row[0]).lower() == ('ipmi_host_data'):
                    print("ipmi_host_data header found at row %s" % str(row_i + 1))
                    host_data_found = True
                continue

            # the column titles should be in the next row
            if not title_indexes:
                col_i = 0
                for col in row:
                    if col.lower() == 'zboot_service':
                        title_indexes['zboot_service'] = col_i
                    if col.lower() == 'ipmi_service':
                        title_indexes['ipmi_service'] = col_i
                    if col.lower() == 'mac':
                        title_indexes['mac'] = col_i
                    if col.lower() == 'ip':
                        title_indexes['ip'] = col_i
                    if col.lower() == 'network':
                        title_indexes['network'] = col_i
                    if col.lower() == 'hostname':
                        title_indexes['hostname'] = col_i
                    if col.lower() == 'lkrn_url':
                        title_indexes['lkrn_url'] = col_i
                    col_i += 1
                
                # check required columns
                for item in ('zboot_service', 'ipmi_service', 'mac', 'ip', 'network', 'lkrn_url'):
                    try:
                        title_indexes[item]
                    except KeyError:
                        raise RuntimeError("key '%s' was not provided for the ipmi_host_data at row %s" % (item, str(row_i + 1)))

                continue
            
            # keep adding ipmi hosts till empty row or EOF
            if row[0] in (None, "") and row[1] in (None, ""):
                print('Host data ended at row %s' % str(row_i + 1))
                break

            # if service already exists, skip
            s = robot.services.find(name=row[title_indexes['hostname']])
            if len(s) > 0:
                print("There is already a service running for host %s. Skipping to next host" % row[title_indexes['hostname']])
                continue

            data = {}
            data["zerobootClient"] = row[title_indexes['zboot_service']]
            data["mac"] = row[title_indexes['mac']].lower()
            data["ip"] = row[title_indexes['ip']]
            data["hostname"] = row[title_indexes['hostname']]
            data["network"] = row[title_indexes['network']]
            data["lkrn_url"] = row[title_indexes['lkrn_url']]
            data["ipmiClient"] = row[title_indexes['ipmi_service']]

            host_service = robot.services.create(
                "github.com/zero-os/0-boot-templates/zeroboot_ipmi_host/0.0.1",
                data["hostname"],
                data=data,
            )
            host_service.schedule_action('install').wait(die=True)

            hosts.append(data["hostname"])

        else:
            if not host_data_found:
                print("No ipmi_host_data was found")
            else:
                print("ipmi_host_data ended at last row")

    return hosts

def add_hosts_pool_service(robot, hosts, pool_name):
    """Creates the pool service if it doesn't exist and adds all provided hosts in that pool
    
    Arguments:
        robot {ZRobot} -- Robot instance
        hosts [str] -- List of hostnames to add to the pool
        pool_name {str} -- Name to give the pool service
    """
    pool_service = robot.services.find_or_create(
        "github.com/zero-os/0-boot-templates/zeroboot_pool/0.0.1",
        pool_name,
        data={}
    )

    for host in hosts:
        # add host to pool
        pool_service.schedule_action('add', args={'host': host}).wait(die=True)

if __name__ == "__main__":
    main(sys.argv)
