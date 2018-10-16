import time
from json import JSONDecodeError

from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import (SERVICE_STATE_ERROR, SERVICE_STATE_OK,
                                      SERVICE_STATE_SKIPPED,
                                      SERVICE_STATE_WARNING, StateCheckError)

NODE_CLIENT = 'local'


class Minio(TemplateBase):

    version = '0.0.1'
    template_name = "minio"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.add_delete_callback(self.uninstall)
        self.recurring_action('_monitor', 30)  # every 30 seconds

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
            self.state.delete('status', 'running')
            self.start()
            if self._minio_sal.is_running():
                self.state.set('status', 'running', 'ok')
        else:
            self.state.set('status', 'running', 'ok')

    @property
    def _node_sal(self):
        return j.clients.zos.get(NODE_CLIENT)

    @property
    def _minio_sal(self):
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
            'tlog_namespace': self.data.get('tlog').get('namespace'),
            'tlog_address': self.data.get('tlog').get('address'),
            'master_namespace': self.data.get('master').get('namespace'),
            'master_address': self.data.get('master').get('address'),
            'block_size': self.data['blockSize'],
        }
        return j.sal_zos.minio.get(**kwargs)

    def node_port(self):
        return self._minio_sal.node_port

    def install(self):
        self.logger.info('Installing minio %s' % self.name)
        self.state.set('actions', 'install', 'ok')

    def start(self):
        """
        start minio server
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Starting minio %s' % self.name)
        minio_sal = self._minio_sal
        minio_sal.start()
        self.state.set('actions', 'start', 'ok')
        self.state.set('status', 'running', 'ok')

    def stop(self):
        """
        stop minio server
        """
        self.state.check('actions', 'install', 'ok')
        self.logger.info('Stopping minio %s' % self.name)
        self._minio_sal.stop()
        self.state.delete('actions', 'start')
        self.state.delete('status', 'running')

    def uninstall(self):
        self.logger.info('Uninstalling minio %s' % self.name)
        self._minio_sal.destroy()
        self.state.delete('actions', 'install')
        self.state.delete('status', 'running')

    def update_zerodbs(self, zerodbs):
        self.data['zerodbs'] = zerodbs
        # if minio is running and we update the config, tell it to reload the config
        minio_sal = self._minio_sal
        if minio_sal.is_running():
            minio_sal.create_config()
            minio_sal.reload()

    def update_tlog(self, namespace, address):
        self.data['tlog'] = {
            'namespace': namespace,
            'address': address
        }
        # if minio is running and we update the config, tell it to reload the config
        minio_sal = self._minio_sal
        if minio_sal.is_running():
            minio_sal.create_config()
            minio_sal.reload()

    def update_master(self, namespace, address):
        self.data['master'] = {
            'namespace': namespace,
            'address': address
        }
        # if minio is running and we update the config, tell it to reload the config
        minio_sal = self._minio_sal
        if minio_sal.is_running():
            minio_sal.create_config()
            minio_sal.reload()

    def _process_logs(self):
        def callback(level, msg, flag):
            health_monitoring(self.state, level, msg, flag)

        while True:
            # wait for the process to be running before processing the logs
            try:
                self.state.check('status', 'running', 'ok')
            except StateCheckError:
                time.sleep(5)
                continue

            # once the process is started, start monitoring the logs
            # the greenlet will parse the stream of logs
            # and self-heal when needed
            gl = self.gl_mgr.add("minio_process", self._minio_sal.stream(callback))
            # we block here until the process stops streaming (usually that means the process has stopped)
            gl.join()


def health_monitoring(state, level, msg, flag):
    if level in [LOG_LVL_MESSAGE_INTERNAL, LOG_LVL_OPS_ERROR, LOG_LVL_CRITICAL_ERROR]:
        msg = j.data.serializer.json.loads(msg)
        if 'data_shard' in msg:
            state.set('data_shards', msg['data_shard'], SERVICE_STATE_ERROR)
        if 'tlog_shard' in msg:
            state.set('tlog_shards', msg['tlog_shard'], SERVICE_STATE_ERROR)


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
