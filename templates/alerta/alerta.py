import requests
from jumpscale import j
from zerorobot.template.base import TemplateBase

OK_STATES = ['OK', 'SKIPPED']
class Alerta(TemplateBase):

    version = '0.0.1'
    template_name = 'alerta'

    def __init__(self, name, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.headers = {
            "Authorization": "Bearer {}".format(self.data['apikey']),
            "Content-type": "application/json"
        }

    def validate(self):
        for param in ['url', 'apikey']:
            if not self.data[param]:
                raise ValueError("parameter '%s' needs to be set" % (param))

    def process_healthcheck(self, name, healcheck_result):
        category = healcheck_result['category'].lower()
        hid = healcheck_result['id']
        resource = healcheck_result['resource']
        envname = self.data['envname']
        for message in healcheck_result['messages']:
            uid = '{}_{}_{}'.format(name, hid, message['id'])
            alert = get_alert(self, uid)
            to_send_alert = False
            if alert:
                if alert['severity'] in OK_STATES:
                    close_alert(self, alert['id'])
                elif alert['severity'] != message['status'] or alert['text'] != message['text']:
                    to_send_alert = True
            elif message['status'] not in OK_STATES:
                to_send_alert = True
            if to_send_alert:
                self.logger.info("Sending alert with status {severity} ({uid}) to alerta server".format(severity=message['status'],uid=uid))
                report_data = {
                    'attributes': {},
                    'resource': uid,
                    'text': message['text'], 
                    'environment': envname,
                    'severity': message['status'],
                    'event': category,
                    'tags': [],
                    'service': [resource]
                }
                send_alert(self, report_data)

def get_alert(service, resource):
    """
    Get an entry from alerta
    :param service: alerta service
    :param resource: unique resource id of required entry
    :return: dict
    """
    resp = requests.get(service.data['url'] + "/alerts",
                        params={'environment': service.data['envname'], 'resource': resource},
                        headers=service.headers)

    if resp.status_code != 200:
        service.logger.info("Couldn't get data from alerta server, error code was %s" % resp.status_code)
    elif resp.json()['alerts']:
        alert = resp.json()['alerts'][0]
        if alert['status'] in ['open', 'ack']:
            return alert

def send_alert(service, data):
    """
    Add new entry to alerta
    :param service: alerta service
    :param data: dict representing the new alert
    :return:
    """
    resp = requests.post(service.data['url'] + "/alert", json=data, headers=service.headers)
    if resp.status_code != 201:
        service.logger.error("Couldn't sent alert, error code was %s" % resp.status_code)

def close_alert(service, alert_id):
    """
    Add new entry to alerta
    :param service: alerta service
    :param alert_id: alert id to change its state to closed
    :return:
    """
    resp = requests.put(service.data['url'] + "/alert/{}/status".format(alert_id),
                        json={'status': 'closed', 'text': 'Closed because check has passed'},
                        headers=service.headers)

    if resp.status_code != 200:
        service.logger.info("Couldn't close alert, error code was %s" % resp.status_code)
