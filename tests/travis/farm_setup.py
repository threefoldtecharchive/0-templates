#python script for 0-core testcases
import os
from argparse import ArgumentParser
from subprocess import Popen, PIPE
import random
import uuid
import time
import shlex
from jumpscale import j
from termcolor import colored
from multiprocessing import Process, Manager

SETUP_ENV_SCRIPT= "tests/travis/setup_env.sh"
SETUP_ENV_SCRIPT_NAME = "setup_env.sh"

class Utils(object):
    def __init__(self, options):
        self.options = options

    def run_cmd(self, cmd, timeout=20):
        now = time.time()
        while time.time() < now + timeout:
            sub = Popen([cmd], stdout=PIPE, stderr=PIPE, shell=True)
            out, err = sub.communicate()
            if sub.returncode == 0:
                return out.decode('utf-8')
            elif any(x in err.decode('utf-8') for x in ['Connection refused', 'No route to host']):
                time.sleep(1)
                continue
            else:
                break
        raise RuntimeError("Failed to execute command.\n\ncommand:\n{}\n\n{}".format(cmd, err.decode('utf-8')))

    def stream_run_cmd(self, cmd):
        sub = Popen(shlex.split(cmd), stdout=PIPE)
        while True:
            out = sub.stdout.readline()
            if out == b'' and sub.poll() is not None:
                break
            if out:
                print(out.strip())
        rc = sub.poll()
        return rc

    def send_script_to_remote_machine(self, script, ip, password, branch):
        cmd = 'wget "https://raw.githubusercontent.com/threefoldtech/0-templates/{}/tests/travis/setup_env.sh"'.format(branch)
        cmd = 'sshpass -p {} ssh -o StrictHostKeyChecking=no  root@{} {}'.format(password, ip, cmd)
        self.run_cmd(cmd)

    def run_cmd_on_remote_machine(self, cmd, ip, password):
        templ = 'sshpass -p {} ssh -o StrictHostKeyChecking=no  root@{} {}'
        cmd = templ.format(password, ip, cmd)
        return self.stream_run_cmd(cmd)

    def run_cmd_on_remote_machine_without_stream(self, cmd, ip, port, password):
        templ = 'sshpass -p {} ssh -o StrictHostKeyChecking=no  root@{} {}'
        cmd = templ.format(password,ip, cmd)
        return self.run_cmd(cmd)

    def get_farm_available_node_to_execute_testcases(self):
        capacity = j.clients.threefold_directory.get(interactive=False)
        resp = capacity.api.ListCapacity(query_params={'farmer': 'kristof-farm'})[1]
        nodes = resp.json() #nodes
        return random.choice(nodes)

def main(options):
    utils = Utils(options)
    # Send the script to setup the envirnment and run testcases 
    utils.send_script_to_remote_machine(SETUP_ENV_SCRIPT, options.vm_ip, options.vm_password, options.branch)

    # get available node to run testcaases against it 
    print('* get available node to run test cases on it ')
    zos_available_node = utils.get_farm_available_node_to_execute_testcases()
    node_robot_address = zos_available_node["robot_address"][7:-5]
    print('* The available node robot {} '.format(node_robot_address))
    
    # Access the ubuntu vm and install requirements  
    cmd = 'bash {script} {branch} {zrobot} {zt_token} {zt_network}'.format(script=SETUP_ENV_SCRIPT_NAME, branch=options.branch, zrobot=node_robot_address, zt_token=options.zt_token,zt_network= options.zt_network)
    utils.run_cmd_on_remote_machine(cmd, options.vm_ip, options.vm_password)

        
if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-v", "--vm_ip", type=str, dest="vm_ip", required=True,
                        help="IP of the zeroos machine that will be used")
                    
    parser.add_argument("-b", "--branch", type=str, dest="branch", required=True,
                        help="0-core branch that the tests will run from")

    parser.add_argument("-t", "--zt_token", type=str, dest="zt_token", default='sgtQtwEMbRcDgKgtHEMzYfd2T7dxtbed', required=True,
                        help="zerotier token that will be used for the 0-templates tests")

    parser.add_argument("-z", "--zt_network", type=str, dest="zt_network", default='sgtQtwEMbRcDgKgtHEMzYfd2T7dxtbed', required=True,
                        help="zerotier network that will be used for the 0-templates tests")

    parser.add_argument("-p", "--password", type=str, dest="vm_password", default='root', required=True,
                        help="js vm password")

    options = parser.parse_args()
    main(options)

