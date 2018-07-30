import time

from js9 import j

from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError

RESERVATION_TEMPLATE = "github.com/zero-os/0-boot-templates/zeroboot_reservation/0.0.1"
SUPPORTED_TEMPLATES = ("github.com/zero-os/0-boot-templates/zeroboot_racktivity_host/0.0.1", "github.com/zero-os/0-boot-templates/zeroboot_ipmi_host/0.0.1")

class ZerobootPool(TemplateBase):

    version = '0.0.1'
    template_name = "zeroboot_pool"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)

    def validate(self):
        # check if all zboot instances exist and installed
        for zbh in self.data['zerobootHosts']:
            self._validate_host(zbh)

            if self.data['zerobootHosts'].count(zbh) > 1:
                raise ValueError("zboot host '%s' is present more than once in the pool" % zbh)


    def _validate_host(self, zbh):
        """ checks if a single zeroboot host service exists and is installed
        
        Arguments:
            zbh str -- Name of the zeroboot host service
        
        Raises:
            ValueError -- Zeroboot host was already present in hosts list
            RuntimeError -- Zeroboot host service not found
            StateCheckError -- Zeroboot host service was not installed
        """
        s = self.api.services.get(name=zbh)
        # check template uid if ipmi or racktivity host
        if not s.template_uid in  SUPPORTED_TEMPLATES:
            raise RuntimeError("Instance %s is not in %s" % (zbh, SUPPORTED_TEMPLATES))

        try:
            s.state.check('actions', 'install', 'ok')
        except StateCheckError:
            raise StateCheckError("zeroboot host %s was not installed" % zbh)

    def add(self, host):
        """ Adds a single zeroboot host to the pool
        
        Arguments:
            host str -- Name of the zeroboot host service
        """
        # check if it's not a duplicate
        if host in self.data["zerobootHosts"]:
            raise ValueError("zboot host '%s' is already present in the pool" % host)
            
        self._validate_host(host)

        self.data["zerobootHosts"].append(host)

    def remove(self, host):
        """ Removes a single zeroboot host from the pool
        
        Arguments:
            host str -- Name of the zeroboot host service
        """
        try:
            self.data["zerobootHosts"].remove(host)
        except ValueError:
            self.logger.debug("host '%s' was not in the list, skipping removal" % host)
            pass

    def unreserved_host(self, caller_guid):
        """ Returns a zeroboot host instance that has not been reserved yet.
        
        Arguments:
            caller_guid str -- guid of the service calling this action
        
        Raises:
            ValueError -- No hosts are available anymore
        
        Returns:
            str -- zeroboot host instance
        """
        reservations = self.api.services.find(template_uid=RESERVATION_TEMPLATE)
        reserved_hosts = []
        for reservation in reservations:
            # skip reservation calling to reserve a host
            if reservation.guid == caller_guid:
                continue
            # skip not installed reservations
            try:
                reservation.state.check('actions', 'install', 'ok')
            except StateCheckError:
                continue

            # add to reserved list
            reserved_hosts.append(reservation.schedule_action('host_instance').wait(die=True).result)

        for zbh in self.data['zerobootHosts']:
            # get the service of the instance and retrieve the host from that
            if not zbh in reserved_hosts:
                return zbh
        raise ValueError("No free hosts available")

    def pool_hosts(self):
        """ Returns the hosts in the pool
        
        Returns:
            [str] -- A list of strings that contains the hosts in the pool
        """

        return self.data['zerobootHosts']

    def power_on(self, interval=1):
        """ Powers on all the hosts in the pool
        
        Keyword Arguments:
            interval int -- Interval before turning on the next host (default: {1})
        """
        for host in self.data['zerobootHosts']:
            s = self.api.services.get(name=host)
            s.schedule_action("power_on").wait(die=True)
            time.sleep(interval)

    def power_off(self,interval=1):
        """ Powers off all the hosts in the pool
        
        Keyword Arguments:
            interval int -- Interval before turning off the next host (default: {1})
        """
        for host in self.data['zerobootHosts']:
            s = self.api.services.get(name=host)
            s.schedule_action("power_off").wait(die=True)
            time.sleep(interval)

    def power_cycle(self, interval=1):
        """ Power cycles all the hosts in the pool 
        
        Keyword Arguments:
            interval {int} -- [description] (default: {1})
        """
        for host in self.data['zerobootHosts']:
            s = self.api.services.get(name=host)
            s.schedule_action("power_cycle").wait(die=True)
            time.sleep(interval)
