import time

from js9 import j

from zerorobot.template.base import TemplateBase
from zerorobot.template.state import StateCheckError

class ZerobootRacktivityHost(TemplateBase):

    version = '0.0.1'
    template_name = "zeroboot_racktivity_host"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
        self.__network = None
        self.__host = None
        self.__zboot = None

    @property
    def _zeroboot(self):
        """ Returns zeroboot client
        
        Returns:
            ZerobootClient -- zeroboot JS client
        """
        if not self.__zboot:
            self.__zboot = j.clients.zboot.get(self.data['zerobootClient'], interactive=False)

        return self.__zboot

    @property
    def _racktivities(self):
        """ Returns list of Racktivity device settings that correspond to the host
        
        Returns:
            [{'client', 'port', 'powermodule'}] -- List of racktivity device settings
        """
        result = []
        for device in self.data['racktivities']:
            r = {}
            r['client'] = j.clients.racktivity.get(device['client'], interactive=False)
            r['port'] = device['port']
            r['powermodule'] = device['powermodule']

            result.append(r)

        return result

    @property
    def _network(self):
        """ Returns the zeroboot network of the host
        
        Returns:
            ZerobootClient.Network -- Zeroboot network
        """
        if not self.__network:
            self.__network =  self._zeroboot.networks.get(self.data['network'])

        return self.__network

    @property
    def _host(self):
        """ Returns zeroboot host for this service
        
        Returns:
            ZerobootClient.Host -- Zeroboot Host
        """
        if not self.__host:
             self.__host = self._network.hosts.get(self.data['hostname'])

        return  self.__host

    def validate(self):
        for key in ['zerobootClient', 'racktivities', 'mac', 'ip', 'network', 'hostname']:
            if not self.data.get(key):
                raise ValueError("data key '%s' not specified." % key)

        # check if clients exists
        if self.data['zerobootClient'] not in j.clients.zboot.list():
            raise LookupError("No zboot client instance found named '%s'" % self.data['zerobootClient'])

        for r in self.data['racktivities']:
            if r['client'] not in j.clients.racktivity.list():
                raise LookupError("No racktivity client instance found named '%s'" % r['client'])
            
            p = r.get('port')
            try:
                int(p)
            except (ValueError, TypeError):
                raise ValueError("Racktivity portnumber was not valid. Found: '%s'" % p)

    def install(self):
        # add host to zeroboot
        if self.data['hostname'] in self._network.hosts.list():
            self.logger.info("hostname was found in network")
            if self.data['mac'] != self._host.mac:
                raise RuntimeError("Host was found in the network but mac address did not match (Found: '%s', configured: '%s')" % (self._host.mac, self.data['mac']))
            if self.data['ip'] != self._host.address:
                raise RuntimeError("Host was found in the network but ip address did not match (Found: '%s', configured: '%s')" % (self._host.address, self.data['ip']))
        else:
            self.logger.info("adding host to network")
            self._network.hosts.add(self.data['mac'], self.data['ip'], self.data['hostname'])

        if self.data.get('lkrnUrl'):
            self._host.configure_ipxe_boot(self.data['lkrnUrl'])

        self.state.set('actions', 'install', 'ok')
        self.data['powerState'] = self.power_status()

    def uninstall(self):
        # remove host from zeroboot
        self._network.hosts.remove(self.data['hostname'])
        self.state.delete('actions', 'install')

    def host(self):
        """ Returns the hostname of the node
        
        Returns:
            str -- hostname
        """
        self.state.check('actions', 'install', 'ok')

        return self.data['hostname']

    def ip(self):
        """ Returns the ip address of the node
        
        Returns:
            str -- ip address
        """
        self.state.check('actions', 'install', 'ok')

        return self.data['ip']
    
    def power_on(self):
        """ Powers on host
        """
        self.state.check('actions', 'install', 'ok')

        for r in self._racktivities:
            self._zeroboot.port_power_on(r['port'], r['client'], r['powermodule'])

        self.data['powerState'] = True

    def power_off(self):
        """ Powers off host
        """
        self.state.check('actions', 'install', 'ok')

        for r in self._racktivities:
            self._zeroboot.port_power_off(r['port'], r['client'], r['powermodule'])

        self.data['powerState'] = False

    def power_cycle(self):
        """ Power cycles host
        """
        self.state.check('actions', 'install', 'ok')
        
        # don't for loop the racktivities and power cycle them as if they are redundant, the host will stay on
        self.power_off()
        time.sleep(5)
        self.power_on()

        # power cycle always ends with a turned on machine
        self.data['powerState'] = True

    def power_status(self, fix_mismatch=True):
        """ Power state of host
        
        Returns:
            bool -- True if on, False if off
        """
        self.state.check('actions', 'install', 'ok')

        # get powerstatus of each device, if all match return first result
        statuses = self._list_power_status()

        if len(statuses) == 1:
            return statuses[0]

        match = True
        comp =  statuses[0]
        for s in statuses:
            if comp != s:
                match = False
                break

        if match:
            return statuses[0]

        # if not match raise Error
        # (if fix_mismatch) set last set powerstate to all devices and check power status again
        if not fix_mismatch:
            raise RuntimeError("The power status of the different racktivity devices for host %s did not match" % self._host)
        else:
            if self.data['powerState']:
                self.power_on()
            else:
                self.power_off()

            statuses = self._list_power_status()

            match = True
            comp =  statuses[0]
            for s in statuses:
                if comp != s:
                    match = False
                    break

            if match:
                return statuses[0]

            raise RuntimeError("The power status of the different racktivity devices for host %s did not match after fixup attempt" % self._host)

    def _list_power_status(self):
        """ Returns list of powerstatuses of all devices
        
        Returns:
            [bool] -- List of power states of the racktivity clients
        """
        result = []

        for r in self._racktivities:
            state = self._zeroboot.port_info(r['port'], r['client'], r['powermodule'])[1]
            if state is None:
                raise RuntimeError("Racktivity client (%s) returned invalid power state for host %s" % 
                    (r['client'].config.instance, self._host))

            result.append(state)

        return result

    def monitor(self):
        """Checks if the power status of the host is the same as the last called power_on/power_off action
        If the state does not match, the last power state set trough an action will be set on the host.
        """
        self.state.check('actions', 'install', 'ok')

        if self.data['powerState'] != self.power_status():
            self.logger.debug('power state did not match')
            if self.data['powerState']:
                self.logger.debug('powering on host to match internal saved power state')
                self.power_on()
            else:
                self.logger.debug('powering off host to match internally saved power state')
                self.power_off()

    def configure_ipxe_boot(self, lkrn_url):
        """ Configure the IPXE boot settings of the host
        
        Arguments:
            lkrn_url str -- URL that points to a LKRN file to boot from that includes boot parameters. E.g.: https://bootstrap.gig.tech/krn/master/0/
        """
        self.state.check('actions', 'install', 'ok')

        if lkrn_url == self.data['lkrnUrl']:
            return

        self._host.configure_ipxe_boot(lkrn_url)
        self.data['lkrnUrl'] = lkrn_url
