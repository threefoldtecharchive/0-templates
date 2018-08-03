import os

from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError
from zerorobot.service_collection import ServiceNotFoundError

FLIST_ZROBOT_DEFAULT = 'https://hub.gig.tech/gig-official-apps/zero-os-0-robot-latest.flist'
CONTAINER_TEMPLATE = 'github.com/threefoldtech/0-templates/container/0.0.1'
NODE_CLIENT = 'local'


class Zrobot(TemplateBase):

    version = '0.0.1'
    template_name = "zrobot"

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.recurring_action('_monitor', 30)  # every 30 seconds

    def validate(self):
        if self.data.get('configRepo') and not self.data.get('sshkey'):
            raise ValueError("Need to specify sshkey when specifying configRepo")
        if self.data.get('dataRepo') and not self.data.get('sshkey'):
            raise ValueError("Need to specify sshkey when specifying dataRepo")
        if self.data.get('flist') is None or self.data.get('flist') == '':
            self.data['flist'] = FLIST_ZROBOT_DEFAULT

    @property
    def node_sal(self):
        return j.clients.zos.get(NODE_CLIENT)

    @property
    def _container_name(self):
        return "container-%s" % self.guid

    def _get_container(self):
        ports = None
        nics = self.data.get('nics')
        if not nics:
            nics = [{'type': 'default'}]

            port = self.data.get('port')
            if not port:
                freeports = self.node_sal.freeports(baseport=6600, nrports=1)
                if not freeports:
                    raise RuntimeError("can't find a free port to expose the robot")
                self.data['port'] = freeports[0]

            ports = ['%s:6600' % self.data['port']]

        data = {
            'flist': self.data['flist'],
            'nics': nics,
            'hostname': self.name,
            'privileged': False,
            'ports': ports,
            'env': [
                {'name': 'LC_ALL', 'value': 'C.UTF-8'},
                {'name': 'LANG', 'value': 'C.UTF-8'},
                {'name': 'SSH_AUTH_SOCK', 'value': '/tmp/sshagent_socket'},
                {'name': 'HOME', 'value': '/root'}
            ]
        }

        sp = self.node_sal.storagepools.get('zos-cache')
        try:
            fs = sp.get(self.guid)
        except ValueError:
            fs = sp.create(self.guid)

        # prepare persistant volume to mount into the container
        node_fs = self.node_sal.client.filesystem
        ssh_vol = os.path.join(fs.path, 'ssh')
        jsconfig_vol = os.path.join(fs.path, 'jsconfig')
        data_vol = os.path.join(fs.path, 'data')
        for vol in (ssh_vol, jsconfig_vol, data_vol):
            node_fs.mkdir(vol)

        data['mounts'] = [
            {'source': ssh_vol,
             'target': '/root/.ssh'},
            {'source': jsconfig_vol,
             'target': '/root/jumpscalehost/cfg'},
            {'source': data_vol,
             'target': '/opt/var/data/zrobot/zrobot_data'},
            {'source': '/var/run/redis.sock',  # mount zero-os redis socket into container, so the robot can talk to the os directly
             'target': '/tmp/redis.sock'}
        ]

        return self.api.services.find_or_create(CONTAINER_TEMPLATE, self._container_name, data)

    @property
    def sshkey_path(self):
        if self.data.get('sshkey'):
            return '/root/.ssh/id_rsa'

    @property
    def zrobot_sal(self):
        container_sal = self.node_sal.containers.get(self._container_name)
        interval = self.data.get('autoPushInterval') or None
        return j.clients.zrobot.get(
            container=container_sal,
            port=6600,
            template_repos=self.data['templates'],
            data_repo=self.data.get('dataRepo'),
            config_repo=self.data.get('configRepo'),
            config_key=self.sshkey_path,
            organization=(self.data.get('organization') or None),
            auto_push=True if interval else False,
            auto_push_interval=interval,
        )

    def get_port(self):
        """returns the port of the created robot

        Returns:
            int -- portnumber of host
        """
        self.state.check('actions', 'start', 'ok')
        if self.data.get('port'):
            return self.data['port']

    def install(self, force=False):
        try:
            self.state.check('actions', 'install', 'ok')
            if not force:
                return
        except StateCheckError:
            pass

        container = self._get_container()
        container.schedule_action('install').wait(die=True)
        if self.data.get('sshkey'):
            container_sal = container.container_sal
            container_sal.client.filesystem.mkdir('/root/.ssh')
            container_sal.upload_content(self.sshkey_path, self.data['sshkey'])
            container_sal.client.filesystem.chmod(self.sshkey_path, int('400', 8))

        self.zrobot_sal.start()
        self.state.set('actions', 'install', 'ok')
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def start(self):
        container = self._get_container()
        container.schedule_action('start').wait(die=True)

        self.zrobot_sal.start()
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def stop(self):
        self.state.check('actions', 'start', 'ok')
        try:
            self.zrobot_sal.stop()
        except (ServiceNotFoundError, LookupError):
            pass
        self.state.delete('actions', 'start')
        self.state.delete('status', 'running')

    def upgrade(self):
        """
        upgrade the container with an updated flist
        this is done by stopping the container and respawn again with the updated flist
        """
        # stop the robot process
        self.stop()

        # force to stop the container
        try:
            contservice = self.api.services.get(name=self._container_name)
            contservice.schedule_action('stop').wait(die=True)
        except (ServiceNotFoundError, LookupError):
            pass

        # restart the robot in a new container
        self.start()

    def uninstall(self):

        try:
            container = self.api.services.get(name=self._container_name)
            self.zrobot_sal.stop()
            container.schedule_action('uninstall').wait(die=True)
            container.delete()
        except (ServiceNotFoundError, LookupError):
            pass

        try:
            # cleanup filesystem used by this robot
            storagepool_sal = self.node_sal.storagepools.get('zos-cache')
            fs_sal = storagepool_sal.get(self.guid)
            fs_sal.delete()
        except ValueError:
            # filesystem doesn't exist, nothing else to do
            pass

        self.state.delete('actions', 'install')
        self.state.delete('status', 'running')

    def _monitor(self):
        self.state.check('actions', 'install', 'ok')
        self.state.check('actions', 'start', 'ok')

        try:
            self.api.services.get(name=self._container_name)  # check that container service exists
            if self.zrobot_sal and self.zrobot_sal.is_running():
                self.state.set('status', 'running', 'ok')
                return
        except (ServiceNotFoundError, LookupError):
            self.state.delete('status', 'running')

        # try to start
        self.start()
