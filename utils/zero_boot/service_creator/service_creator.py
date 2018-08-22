import os
import click

from jumpscale import j
from zerorobot.template.state import StateCheckError
from unittest.mock import MagicMock

import csv_parser


@click.command()
@click.option("-d", "--data", help="CSV file to read the host data from", required=True)
@click.option("-r", "--robot", help="0-robot instance to use", required=True)
@click.option("-p", "--pool", help="Puts all hosts in a pool with provided name", required=False)
@click.option("-c", "--clean", help="Start from clean env. Deletes all reservation, pool, racktivity host, racktivity client, zeroboot and ssh services from the robot it has access to.", is_flag=True, default=False)
@click.option("--debug", help="Start from clean env. Deletes all reservation, pool, racktivity host, racktivity client, zeroboot and ssh services from the robot it has access to.", is_flag=True, default=False)
def main(data, robot, pool, clean):

    if robot == "debug":
        robot = MagicMock()
    else:
        robot = j.clients.zrobot.robots[robot]

    if clean:
        clean_env(robot)

    _, ext = os.path.splitext(data)
    if ext == '.json':
        data_file = j.data.serializer.json.load(data)
    elif ext == '.yaml':
        data_file = j.data.serializer.yaml.load(data)
    elif ext == '.csv':
        data_file = csv_parser.parse(data)
    else:
        raise ValueError("data file extension not supported. Only supproted type are json, yaml and csv")

    pool_name = data_file.pop('zeroboot_pool')

    # create_ssh_services(robot, args.data_file)
    hosts = []
    for template, instances in data_file.items():
        for instance, data in instances.items():
            service = robot.services.find_or_create(
                "github.com/zero-os/0-boot-templates/%s/0.0.1" % template,
                instance,
                data=data)
            if template in ['zeroboot_racktivity_host', 'zeroboot_ipmi_host']:
                hosts.append(service)
                try:
                    service.state.check('actions', 'install', 'ok')
                except StateCheckError:
                    service.schedule_action('install').wait(die=True)

    pool = robot.services.find_or_create(
        "github.com/zero-os/0-boot-templates/zeroboot_pool/0.0.1",
        pool_name,
        data={})

    for host in hosts:
        pool.schedule_action('add', args={'host': host.name}).wait(die=True)


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

    for template in ['zeroboot_reservation', 'zeroboot_pool', 'zeroboot_racktivity_host',
                     'racktivity_client', 'zeroboot_client', 'ssh_client']:

        for service in robot.services.find(template_uid='github.com/zero-os/0-boot-templates/%s/0.0.1' % template):
            if template == 'zeroboot_reservation':
                service.schedule_action("uninstall").wait(die=True)
            service.delete()

    print("Environment should be cleaned up now!")


if __name__ == "__main__":
    main()
