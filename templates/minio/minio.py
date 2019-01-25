import time
from json import JSONDecodeError

import gevent
from gevent.lock import Semaphore
from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry
from zerorobot.template.state import (SERVICE_STATE_ERROR, SERVICE_STATE_OK,
                                      SERVICE_STATE_SKIPPED,
                                      SERVICE_STATE_WARNING, StateCheckError)

PORT_MANAGER_TEMPLATE_UID = 'github.com/threefoldtech/0-templates/node_port_manager/0.0.1'
ALERTA_UID = 'github.com/threefoldtech/0-templates/alerta/0.0.1'

NODE_CLIENT = 'local'


class Minio(TemplateBase):

    version = '0.0.1'
    template_name = "minio"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self._node_sal = j.clients.zos.get(NODE_CLIENT)
        self._healer = Healer(self)
        self.add_delete_callback(self.uninstall)
        self.recurring_action('_monitor', 30)  # every 30 seconds
        self.recurring_action('check_and_repair', 43200)  # every 12 hours

    def validate(self):
        self.state.delete('status', 'running')
        for param in ['zerodbs', 'namespace', 'login', 'password']:
            if not self.data.get(param):
                raise ValueError("parameter '%s' not valid: %s" % (param, str(self.data[param])))

    def _monitor(self):
        self.logger.info('Monitor minio %s' % self.name)
        try:
            self.state.check('actions', 'install', 'ok')
            self.state.check('actions', 'start', 'ok')
        except StateCheckError:
            return

        if not self._minio_sal.is_running():
            self.state.set('status', 'running', 'error')
            self._healer.stop()
            self.install()
            self.start()
            if self._minio_sal.is_running():
                self.state.set('status', 'running', 'ok')
        else:
            self.state.set('status', 'running', 'ok')

        self._healer.start()

    @property
    def _minio_sal(self):
        tlog_namespace = None
        tlog_address = None
        master_namespace = None
        master_address = None

        if self.data['tlog']:
            if self.data['tlog'].get('namespace'):
                tlog_namespace = self.data['tlog']['namespace']
            if self.data['tlog'].get('address'):
                tlog_address = self.data['tlog']['address']

        if self.data['master']:
            if self.data['master'].get('namespace'):
                master_namespace = self.data['master']['namespace']
            if self.data['master'].get('address'):
                master_address = self.data['master']['address']

        kwargs = {
            'name': self.name,
            'node': self._node_sal,
            'namespace': self.data['namespace'],
            'namespace_secret': self.data['nsSecret'],
            'zdbs': self.data['zerodbs'],
            'private_key': self.data['privateKey'],
            'login': self.data['login'],
            'password': self.data['password'],
            'meta_private_key': self.data['metaPrivateKey'],
            'nr_datashards': self.data['dataShard'],
            'nr_parityshards': self.data['parityShard'],
            'tlog_namespace': tlog_namespace,
            'tlog_address': tlog_address,
            'master_namespace': master_namespace,
            'master_address': master_address,
            'block_size': self.data['blockSize'],
            'node_port': self.data['nodePort'],
        }
        return j.sal_zos.minio.get(**kwargs)

    def connection_info(self):
        self.state.check('actions', 'install', 'ok')
        return {
            'public': 'http://%s:%s' % (self._node_sal.public_addr, self.data['nodePort']),
            'storage': 'http://%s:%s' % (self._node_sal.storage_addr, self.data['nodePort']),
        }

    def install(self):
        self.logger.info('Installing minio %s' % self.name)
        self._reserve_port()
        self.state.set('actions', 'install', 'ok')
        self.state.delete('data_shards')
        self.state.delete('tlog_shards')
        self.state.delete('vm')

        for addr in self.data['zerodbs']:
            self.state.set('data_shards', addr, SERVICE_STATE_OK)
        if self.data['tlog']:
            self.state.set('tlog_shards', self.data['tlog']['address'], SERVICE_STATE_OK)

    def start(self):
        """
        start minio server
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Starting minio %s' % self.name)
        minio_sal = self._minio_sal
        minio_sal.start()
        self._healer.start()
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def stop(self):
        """
        stop minio server
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Stopping minio %s' % self.name)
        self._minio_sal.stop()
        self._healer.stop()
        self.state.delete('data_shards')
        self.state.delete('tlog_shards')
        self.state.delete('vm')
        self.state.delete('actions', 'start')
        self.state.delete('status', 'running')

    def uninstall(self):
        self.logger.info('Uninstalling minio %s' % self.name)
        self._healer.stop()
        self._minio_sal.destroy()

        self._release_port()

        self.state.delete('data_shards')
        self.state.delete('tlog_shards')
        self.state.delete('vm')
        self.state.delete('actions', 'install')
        self.state.delete('status', 'running')

    def upgrade(self):
        self.logger.info("upgrading minio")
        self.state.set('upgrade', 'running', 'ok')
        try:
            minio_sal = self._minio_sal
            self._healer.stop()
            minio_sal.stop()
            minio_sal.start()
            self._healer.start()
        finally:
            self.state.delete('upgrade', 'running')

    def update_all(self, zerodbs, tlog, master):
        if zerodbs:
            self.update_zerodbs(zerodbs, reload=False)
        if tlog:
            self.update_tlog(tlog['namespace'], tlog['address'], reload=False)
        if master:
            self.update_master(master['namespace'], master['address'], reload=False)

        minio_sal = self._minio_sal
        if minio_sal.is_running():
            minio_sal.create_config()
            minio_sal.reload()

    def update_zerodbs(self, zerodbs, reload=True):
        self.state.delete('data_shards')

        self.data['zerodbs'] = zerodbs
        # if minio is running and we update the config, tell it to reload the config
        minio_sal = self._minio_sal
        if reload and minio_sal.is_running():
            minio_sal.create_config()
            minio_sal.reload()

        # we consider shards info to be valid when we update them
        for addr in self.data['zerodbs']:
            self.state.set('data_shards', addr, SERVICE_STATE_OK)

    def update_tlog(self, namespace, address, reload=True):
        self.state.delete('vm')
        self.state.delete('tlog_shards')
        self.data['tlog'] = {
            'namespace': namespace,
            'address': address
        }
        # if minio is running and we update the config, tell it to reload the config
        minio_sal = self._minio_sal
        if reload and minio_sal.is_running():
            minio_sal.create_config()
            minio_sal.reload()

        # we consider shards info to be valid when we update them
        if self.data['tlog']:
            self.state.set('tlog_shards', self.data['tlog']['address'], SERVICE_STATE_OK)

    def update_master(self, namespace, address, reload=True):
        self.data['master'] = {
            'namespace': namespace,
            'address': address
        }
        # if minio is running and we update the config, tell it to reload the config
        minio_sal = self._minio_sal
        if reload and minio_sal.is_running():
            minio_sal.create_config()
            minio_sal.reload()

    def check_and_repair(self, block=False):
        if block:
            self._minio_sal.check_and_repair()
        else:
            gevent.spawn(self._minio_sal.check_and_repair)

    @retry(exceptions=ServiceNotFoundError, tries=3, delay=3, backoff=2)
    def _reserve_port(self):
        if self.data['nodePort']:
            return
        port_mgr = self.api.services.get(template_uid=PORT_MANAGER_TEMPLATE_UID, name='_port_manager')
        self.data['nodePort'] = port_mgr.schedule_action(
            "reserve", {"service_guid": self.guid, 'n': 1}).wait(die=True).result[0]

    @retry(exceptions=ServiceNotFoundError, tries=3, delay=3, backoff=2)
    def _release_port(self):
        if not self.data['nodePort']:
            return
        port_mgr = self.api.services.get(template_uid=PORT_MANAGER_TEMPLATE_UID, name='_port_manager')
        port_mgr.schedule_action("release", {"service_guid": self.guid, 'ports': [self.data['nodePort']]})
        self.data['nodePort'] = 0


LOG_LVL_STDOUT = 1
LOG_LVL_STDERR = 2
LOG_LVL_MESSAGE_PUBLIC = 3
LOG_LVL_MESSAGE_INTERNAL = 4
LOG_LVL_LOG_UNKNOWN = 5
LOG_LVL_LOG_STRUCTURED = 6
LOG_LVL_WARNING = 7
LOG_LVL_OPS_ERROR = 8
LOG_LVL_CRITICAL_ERROR = 9
LOG_LVL_STATISTICS = 10
LOG_LVL_RESULT_JSON = 20
LOG_LVL_RESULT_YAML = 21
LOG_LVL_RESULT_TOML = 22
LOG_LVL_RESULT_HRD = 23
LOG_LVL_JOB = 30


class Healer:
    MinioStreamKey = "minio.logs"

    def __init__(self, minio):
        self.service = minio
        self.logger = minio.logger

    def start(self):
        started = False
        try:
            gl = self.service.gl_mgr.get(Healer.MinioStreamKey)
            if gl.started and not gl.ready():
                started = True
        except KeyError:
            started = False

        if not started:
            self.logger.info("start minio logs processing")
            self.service.gl_mgr.add(Healer.MinioStreamKey, self._process_logs)

    def stop(self):
        self.logger.info("stop minio logs processing")
        self.service.gl_mgr.stop(Healer.MinioStreamKey, wait=True, timeout=5)

    def _send_alert(self, ressource, text, tags, event, severity='critical'):
        alert = {
            'attributes': {},
            'resource': ressource,
            'environment': 'Production',
            'severity': severity,
            'event': event,
            'tags': tags,
            'service': [self.service.name],
            'text': text,
        }
        for alerta in self.service.api.services.find(template_uid=ALERTA_UID):
            alerta.schedule_action('send_alert', args={'data': alert})

    def _process_data_shards_event(self, msg):
        addr = msg['shard']
        if addr not in self.service.data['zerodbs']:
            # this is an old shards we dont use anymore
            return

        if 'error' in msg:
            self.service.state.set('data_shards', addr, SERVICE_STATE_ERROR)
        else:
            self.service.state.set('data_shards', addr, SERVICE_STATE_OK)

    def _process_tlog_shard_event(self, msg):
        addr = msg['tlog']
        if 'tlog' in self.service.data and self.service.data['tlog'].get('address') != addr:
            # this is an old shards we dont use anymore
            return

        if 'error' in msg:
            self.service.state.set('tlog_shards', addr, SERVICE_STATE_ERROR)
        else:
            self.service.state.set('tlog_shards', addr, SERVICE_STATE_OK)

    def _process_disk_event(self, msg):
        self.service.state.set('vm', 'disk', 'error')

    def _process_logs(self):
        self.logger.info("processing logs for minio '%s'" % self.service)

        def callback(level, msg, flag):
            if level not in [LOG_LVL_MESSAGE_INTERNAL]:
                return
            # gevent.spawn(self._send_alert(self.service.name, msg, [], 'minio_logs', 'debug'))
            msg = j.data.serializer.json.loads(msg)

            if 'shard' in msg:
                self._process_data_shards_event(msg)
            elif 'tlog' in msg:
                self._process_tlog_shard_event(msg)
            elif 'disk' in msg:
                self._process_disk_event(msg)

        while True:
            # wait for the process to be running before processing the logs
            try:
                self.service.state.check('status', 'running', 'ok')
            except StateCheckError:
                time.sleep(5)
                continue

            # once the process is started, start monitoring the logs
            # this will block until the process stops streaming (usually that means the process has stopped)
            self.logger.info("calling minio stream method")
            self.service._minio_sal.stream(callback)
