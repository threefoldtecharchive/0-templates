import os
import time
import requests

from js9 import j
from zerorobot.service_collection import ServiceNotFoundError
from zerorobot.template.base import TemplateBase
from zerorobot.template.decorator import retry
from zerorobot.template.state import StateCheckError


class BlockCreatorStatusReporter(TemplateBase):
    version = '0.0.1'
    template_name = 'block_creator_status_reporter'

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self._node_ = None
        self._block_creator_ = None
        self.recurring_action('_monitor', 300)  # every 5 minutes

    def validate(self):
        self._url

    @property
    def _block_creator(self):
        if not self._block_creator_:
            try:
                self._block_creator_ = self.api.services.get(template_uid='github.com/threefoldtoken/0-templates/block_creator/0.0.1', name=self.data['blockCreator'])
            except ServiceNotFoundError:
                pass
        return self._block_creator_

    @property
    def _url(self):
        if not hasattr(self, '_url_'):
            self._url_ = self.data['postUrlTemplate'].format(block_creator_identifier=self.data['blockCreatorIdentifier'])
        return self._url_

    @property
    def _node(self):
        if not self._node_:
            try:
                self._node_ = self.api.services.get(template_uid='github.com/zero-os/0-templates/node/0.0.1', name=self.data['node'])
            except ServiceNotFoundError:
                pass
        return self._node_            

    def start(self):
        self.state.set('status', 'running', 'ok')

    def stop(self):
        self.state.delete('status', 'running')

    def _monitor(self):
        try:
            self.state.check('status', 'running', 'ok')
        except StateCheckError:
            return
        
        if self._block_creator:
            consensus_task = self._block_creator.schedule_action('consensus_stat')
            wallet_amount_task = self._block_creator.schedule_action('wallet_amount')
        if self._node:
            stats_task = self._node.schedule_action('stats')
            info_task = self._node.schedule_action('info')


        payload = dict()

        if self._block_creator:
            # Gather chain info
            consensus_task.wait()
            if consensus_task.state == 'ok':
                height = int(consensus_task.result['Height'])
            else:
                height = -1
            wallet_amount_task.wait()
            if wallet_amount_task.state == 'ok':
                status = "unlocked"
            else:
                status = "error"
            
            payload["chain_status"] = {'wallet_status': status, 'block_height': height}

        if self._node:
            # Gather stats info
            stats_task.wait()
            if stats_task.state == 'ok':
                stats = dict()
                payload['stats'] = stats
                for stat_kind, stat in stats_task.result.items():
                    stats[stat_kind] = stat['history']['300']
            
            # Gather node info
            info_task.wait()
            if info_task.state == 'ok':
                payload['info'] = info_task.result

        headers = { 'content-type': 'application/json'}
        requests.request('PUT', self._url, json=payload, headers=headers)
