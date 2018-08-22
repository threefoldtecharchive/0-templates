import csv


def parse(path):
    data = {}
    with open(path, newline='') as csvfile:
        for func in [ssh_client, zeroboot_client, racktivity_client,
                     zeroboot_racktivity_host, ipmi_clients, zeroboot_ipmi_host]:

            # all the method expect to read from the begining of the file
            csvfile.seek(0, 0)
            reader = csv.reader(csvfile, delimiter=',')
            data[func.__name__] = func(reader)
    return data


def ssh_client(reader):
    output = []
    data_found = False
    title_indexes = {}
    row_i = -1
    for row in reader:
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
        data = {}
        data["login"] = row[title_indexes['user']]
        data["password"] = row[title_indexes['password']]
        data["host"] = row[title_indexes['host_address']]
        if title_indexes.get("port") and row[title_indexes["port"]]:
            data["port"] = int(row[title_indexes["port"]])

        output.append(data)
    else:
        if not data_found:
            print("No SSH client data was found")
        else:
            print("SSH client data ended at last row")

    return output


def zeroboot_client(reader):
    output = []
    data_found = False
    title_indexes = {}
    row_i = -1
    for row in reader:
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
        data = {}
        data["networkId"] = row[title_indexes['ztier_network']]
        data["sshClient"] = row[title_indexes['ssh_service']]
        if title_indexes.get("ztier_service") and row[title_indexes["ztier_service"]]:
            data["zerotierClient"] = int(row[title_indexes["ztier_service"]])

        output.append(data)
    else:
        if not data_found:
            print("No Zboot client data was found")
        else:
            print("Zboot client data ended at last row")

    return output


def racktivity_client(reader):
    output = []
    rack_data_found = False
    title_indexes = {}
    row_i = -1
    for row in reader:
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
        data = {}
        data["username"] = row[title_indexes['user']]
        data["password"] = row[title_indexes['password']]
        data["host"] = row[title_indexes['host_address']]
        if title_indexes.get("port") and row[title_indexes["port"]]:
            data["port"] = int(row[title_indexes["port"]])

        output.append(data)
    else:
        if not rack_data_found:
            print("No racktivity client data was found")
        else:
            print("Racktivity client data ended at last row")
    return output


def zeroboot_racktivity_host(reader):
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

    output = []
    hosts = []
    host_data_found = False
    title_indexes = {}
    row_i = -1
    for row in reader:
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

        output.append(data)
    else:
        if not host_data_found:
            print("No host data was found")
        else:
            print("host data ended at last row")

    return output


def ipmi_clients(reader):
    output = []
    ipmi_data_found = False
    title_indexes = {}
    row_i = -1
    for row in reader:
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
        data = {}
        data["username"] = row[title_indexes['user']]
        data["password"] = row[title_indexes['password']]
        data["host"] = row[title_indexes['host_address']]
        if title_indexes.get("port") and row[title_indexes["port"]]:
            data["port"] = int(row[title_indexes["port"]])

        output.append(data)
    else:
        if not ipmi_data_found:
            print("No ipmi client data was found")
        else:
            print("IPMI client data ended at last row")
    return output


def zeroboot_ipmi_host(reader):
    output = []
    host_data_found = False
    title_indexes = {}
    row_i = -1
    for row in reader:
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

        output.append(data)

    else:
        if not host_data_found:
            print("No ipmi_host_data was found")
        else:
            print("ipmi_host_data ended at last row")

    return output
