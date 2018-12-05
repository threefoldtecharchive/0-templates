import os
import click

from Jumpscale import j
from zerorobot.template.state import StateCheckError
from unittest.mock import MagicMock

import csv_parser

logger = j.logger.get('0bootinstaller')


@click.command()
@click.option("-d", "--data", help="CSV file to read the host data from", required=True)
@click.option("-r", "--robot", help="0-robot instance to use", required=True)
@click.option("-p", "--pool", help="Puts all hosts in a pool with provided name", required=False)
@click.option("-c", "--clean", help="Start from clean env. Deletes all reservation, pool, racktivity host, racktivity client, zeroboot and ssh services from the robot it has access to.", is_flag=True, default=False)
@click.option("--debug", help="dry run", is_flag=True, default=False)
def main(data, robot, pool, clean, debug):
    if debug:
        robot = MagicMock()
    else:
        robot = j.clients.zrobot.robots[robot]

    if clean:
        clean_env(robot)

    _, ext = os.path.splitext(data)
    if ext == '.json':
        input = j.data.serializers.json.load(data)
    elif ext == '.yaml':
        input = j.data.serializers.yaml.load(data)
    elif ext == '.csv':
        input = csv_parser.parse(data)
    else:
        raise ValueError("data file extension not supported. Only supproted type are json, yaml and csv")

    pool_name = pool
    if 'zeroboot_pool' in input:
        pool_name = input.pop('zeroboot_pool')

    logger.info("pool name: %s" % pool_name)

    logger.info("start creation of services")

    for template, instances in input.items():
        for instance, data in instances.items():
            logger.info("create service %s %s" % (template, instance))
            service = robot.services.find_or_create(
                "github.com/threefoldtech/0-templates/%s/0.0.1" % template,
                instance,
                data=data)

    hosts = robot.services.find(template_name='zeroboot_racktivity_host') + robot.services.find(template_name='zeroboot_ipmi_host')
    for service in hosts:
        try:
            service.state.check('actions', 'install', 'ok')
            logger.info("\talready installed")
        except StateCheckError:
            logger.info("\tinstall service")
            service.schedule_action('install').wait(die=True)

    logger.info("create service zeroboot_pool %s" % pool_name)
    pool = robot.services.find_or_create(
        "github.com/threefoldtech/0-templates/zeroboot_pool/0.0.1",
        pool_name,
        data={'zerobootHosts': [h.name for h in hosts]})

    logger.info("installation done")


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
    logger.info("Cleaning up environment...")

    for template in ['zeroboot_reservation', 'zeroboot_pool', 'zeroboot_racktivity_host',
                     'racktivity_client', 'zeroboot_client', 'ssh_client']:

        for service in robot.services.find(template_uid='github.com/zero-os/0-boot-templates/%s/0.0.1' % template):
            if template == 'zeroboot_reservation':
                service.schedule_action("uninstall").wait(die=True)
            service.delete()

    logger.info("Environment should be cleaned up now!")


if __name__ == "__main__":
    main()

