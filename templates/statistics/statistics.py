from jumpscale import j
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import timeout

NODE_CLIENT = 'local'


class Statistics(TemplateBase):
    version = '0.0.1'
    template_name = 'statistics'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self._url_ = None
        self._node_ = None
        self.recurring_action('_monitor', 300)  # every 5 minutes

    @property
    def _node_sal(self):
        """
        connection to the node
        """
        return j.clients.zos.get(NODE_CLIENT)

    @property
    def _node(self):
        if not self._node_:
            self._node_ = self.api.services.get(template_account='threefoldtech', template_name='node')
        return self._node_

    def _ensure_db(self):
        db = j.clients.influxdb.get(self.data['influxdbClient'], create=False)
        existing_dbs = db.get_list_database()
        for x in existing_dbs:
            if x['name'] == 'statistics':
                break
        else:
            db.create_database('statistics')
            db.switch_database('statistics')
            db.config.data_set('database', 'statistics')

    def install(self):
        self._ensure_db()
        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        db = j.clients.influxdb.get(self.data['influxdbClient'], create=False)
        existing_dbs = db.get_list_database()
        for x in existing_dbs:
            if x['name'] == 'statistics':
                db.drop_database('statistics')

        self.state.delete('actions', 'install')

    @timeout(60, error_message='Monitor function call timed out')
    def _monitor(self):
        self.state.check('actions', 'install', 'ok')

        self._ensure_db()

        stats_task = self._node.schedule_action('stats')
        stats_task.wait(die=True)

        # Gather stats info
        db = j.clients.influxdb.get(self.data['influxdbClient'], create=False)
        hostname = self._node_sal.client.info.os()['hostname']
        version = self._node_sal.client.ping().split(':', 1)[1].strip()
        for measurement, stat in stats_task.result.items():
            measurement = measurement.split('/')[0]
            tags = {x['key']: x['value'] for x in stat['tags']}
            tags['hostname'] = hostname
            tags['version'] = version
            value = stat['current'].get('300', {}).get('avg')
            db.write_points([{
                "measurement": measurement,
                "tags": tags,
                "fields": {
                    "value": float(value)
                }
            }])
