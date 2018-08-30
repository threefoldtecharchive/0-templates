import os
import datetime
from jumpscale import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError
from zerorobot.template.decorator import timeout


class Statistics(TemplateBase):
    version = '0.0.1'
    template_name = 'statistics'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self._url_ = None
        self._node_ = None
        self.recurring_action('_monitor', 300)  # every 5 minutes

    @property
    def _node(self):
        if not self._node_:
            self._node_ = self.api.services.get(template_account='threefoldtech', template_name='node')
        return self._node_

    def install(self):
        db = j.clients.influxdb.get(self.data['influxdbClient'], create=False)
        dbs = db.config
        if dbs.data['database'] != 'statistics':
            db.create_database('statistics')
            db.switch_database('statistics')
            dbs.data_set('database', 'statistics')

        self.state.set('actions', 'install', 'ok')

    def uninstall(self):
        self.state.delete('actions', 'install')

    @timeout(60, error_message='Monitor function call timed out')
    def _monitor(self):
        self.state.check('actions', 'install', 'ok')
        stats_task = self._node.schedule_action('stats')
        # Gather stats info
        stats_task.wait(die=True)
        db = j.clients.influxdb.get(self.data['influxdbClient'], create=False)
        current_date = datetime.datetime.now()
        for _, stat in stats_task.result.items():
            points = stat['history']['300']
            ps = []
            for point in points:
                ps.append({'measurement': 'statistics', 'tags': point, 'fields': {'Time': current_date.strftime("%I:%M:%S %p")}})
            db.write_points(ps, database='statistics')
