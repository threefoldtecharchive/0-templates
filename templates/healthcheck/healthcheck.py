from jumpscale import j
from zerorobot.template.base import TemplateBase

NODE_TEMPLATE_UID = "github.com/threefoldtech/0-templates/node/0.0.1"


class Healthcheck(TemplateBase):

    version = "0.0.1"
    template_name = "healthcheck"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.recurring_action("_monitor", 600)

    def _monitor(self):
        self.logger.info("Monitoring node %s health check" % self.name)
        self._healthcheck()

    def _healthcheck(self):
        node_sal = self.api.node_sal
        _update_healthcheck_state(self, node_sal.healthcheck.openfiledescriptors())
        _update_healthcheck_state(self, node_sal.healthcheck.cpu_mem())
        _update_healthcheck_state(self, node_sal.healthcheck.rotate_logs())
        _update_healthcheck_state(self, node_sal.healthcheck.network_bond())
        _update_healthcheck_state(self, node_sal.healthcheck.interrupts())
        _update_healthcheck_state(self, node_sal.healthcheck.context_switch())
        _update_healthcheck_state(self, node_sal.healthcheck.threads())
        _update_healthcheck_state(self, node_sal.healthcheck.qemu_vm_logs())
        _update_healthcheck_state(self, node_sal.healthcheck.network_load())
        _update_healthcheck_state(self, node_sal.healthcheck.disk_usage())

        # this is for VM. VM is not implemented yet, and we'll probably not need
        # some cleanup like this anyhow
        # node_sal.healthcheck.ssh_cleanup(job=job)

        # TODO: this need to be configurable
        flist_healhcheck = "https://hub.grid.tf/tf-official-apps/healthcheck.flist"
        with node_sal.healthcheck.with_container(flist_healhcheck) as cont:
            _update_healthcheck_state(self, node_sal.healthcheck.node_temperature(cont))
            _update_healthcheck_state(self, node_sal.healthcheck.powersupply(cont))
            _update_healthcheck_state(self, node_sal.healthcheck.fan(cont))


def _update(service, healcheck_result):
    for rprtr in service.data.get("alerta", []):
        reporter = service.api.services.get(name=rprtr)
        reporter.schedule_action(
            "process_healthcheck", args={"name": service.name, "healcheck_result": healcheck_result}
        )

    category = healcheck_result["category"].lower()
    if len(healcheck_result["messages"]) == 1:
        tag = healcheck_result["id"].lower()
        status = healcheck_result["messages"][0]["status"].lower()
        service.state.set(category, tag, status)
    elif len(healcheck_result["messages"]) > 1:
        for msg in healcheck_result["messages"]:
            tag = ("%s-%s" % (healcheck_result["id"], msg["id"])).lower()
            status = msg["status"].lower()
            service.state.set(category, tag, status)


def _update_healthcheck_state(service, healthcheck):
    if isinstance(healthcheck, list):
        for hc in healthcheck:
            _update(service, hc)
    else:
        _update(service, healthcheck)
