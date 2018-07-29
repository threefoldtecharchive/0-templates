import os
import pytest
from unittest import mock
from unittest.mock import MagicMock

from js9 import j
from zerorobot.template.state import StateCheckError

from JumpScale9Zrobot.test.utils import ZrobotBaseTest
from zeroboot_ipmi_host import ZerobootIpmiHost

class TestZerobootIpmiHostTemplate(ZrobotBaseTest):
    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), ZerobootIpmiHost)
        cls._valid_data = {
            'zerobootClient': 'zboot1-zb',
            'ipmiClient': 'zboot1-ipmi',
            'mac': 'well:this:a:weird:mac:address',
            'ip': '10.10.1.1',
            'network': '10.10.1.0/24',
            'hostname': 'test-01',
            'lkrnUrl': 'some.ixpe.url',
        }

    @mock.patch.object(j.clients, '_ipmi')
    @mock.patch.object(j.clients, '_zboot')
    def test_validation_valid_data(self, zboot, ipmi):
        zboot.list = MagicMock(return_value=[self._valid_data['zerobootClient']])
        ipmi.list = MagicMock(return_value=[self._valid_data['ipmiClient']])

        _ = ZerobootIpmiHost(name="test", data=self._valid_data)

    @mock.patch.object(j.clients, '_ipmi')
    @mock.patch.object(j.clients, '_zboot')
    def test_validation_required_fields(self, zboot, ipmi):
        zboot.list = MagicMock(return_value=[self._valid_data['zerobootClient']])
        ipmi.list = MagicMock(return_value=[self._valid_data['ipmiClient']])

        test_cases = [
            {
                'data': {
                    'ipmiClient': 'zboot1-ipmi',
                    'mac': 'well:this:a:weird:mac:address',
                    'ip': '10.10.1.1',
                    'network': '10.10.1.0/24',
                    'hostname': 'test-01',
                    'lkrnUrl': 'some.ixpe.url',
                },
                'message': "Should fail: missing zerobootClient",
                'missing': 'zerobootClient',
            },
            {
                'data': {
                    'zerobootClient': 'zboot1-zb',
                    'mac': 'well:this:a:weird:mac:address',
                    'ip': '10.10.1.1',
                    'network': '10.10.1.0/24',
                    'hostname': 'test-01',
                    'lkrnUrl': 'some.ixpe.url',
                },
                'message': "Should fail: missing ipmiClient",
                'missing': 'ipmiClient',
            },
            {
                'data': {
                    'zerobootClient': 'zboot1-zb',
                    'ipmiClient': 'zboot1-ipmi',
                    'mac': 'well:this:a:weird:mac:address',
                    'ip': '10.10.1.1',
                    'hostname': 'test-01',
                    'lkrnUrl': 'some.ixpe.url',
                },
                'message': "Should fail: missing network",
                'missing': 'network',
            },
            {
                'data': {
                    'zerobootClient': 'zboot1-zb',
                    'ipmiClient': 'zboot1-ipmi',
                    'mac': 'well:this:a:weird:mac:address',
                    'ip': '10.10.1.1',
                    'network': '10.10.1.0/24',
                    'lkrnUrl': 'some.ixpe.url',
                },
                'message': "Should fail: missing hostname",
                'missing': 'hostname',
            },
            {
                'data': {
                    'zerobootClient': 'zboot1-zb',
                    'ipmiClient': 'zboot1-ipmi',
                    'ip': '10.10.1.1',
                    'network': '10.10.1.0/24',
                    'hostname': 'test-01',
                    'lkrnUrl': 'some.ixpe.url',
                },
                'message': "Should fail: missing mac address",
                'missing': 'mac',
            },
            {
                'data': {
                    'zerobootClient': 'zboot1-zb',
                    'ipmiClient': 'zboot1-ipmi',
                    'network': '10.10.1.0/24',
                    'mac': 'well:this:a:weird:mac:address',
                    'hostname': 'test-01',
                },
                'message': "Should fail: missing ip address",
                'missing': 'ip',
            },
        ]

        for tc in test_cases:
            instance = ZerobootIpmiHost(name="test", data=tc['data'])

            with pytest.raises(
                    ValueError, message="Unexpected success: %s\n\nData: %s" %(tc['message'], tc['data'])) as excinfo:
                instance.validate()
            
            if tc['missing'] not in str(excinfo):
                pytest.fail(
                    "Error message did not contain missing field('%s'): %s" % (tc['missing'], str(excinfo)))

    @mock.patch.object(j.clients, '_ipmi')
    @mock.patch.object(j.clients, '_zboot')
    def test_validate_no_zboot_instance(self, zboot, ipmi):
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)

        zboot.list = MagicMock(return_value=[])
        ipmi.list = MagicMock(return_value=[self._valid_data['ipmiClient']])
        instance.power_status = MagicMock(return_value=True)

        with pytest.raises(LookupError, message="zeroboot instance should not be present") as excinfo:
            instance.validate()
        if "zboot client" not in str(excinfo.value):
            pytest.fail("Received unexpected error message for missing zboot instance: %s" % str(excinfo.value))

    @mock.patch.object(j.clients, '_ipmi')
    @mock.patch.object(j.clients, '_zboot')
    def test_validate_no_ipmi_instance(self, zboot, ipmi):
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)

        zboot.list = MagicMock(return_value=[self._valid_data['zerobootClient']])
        ipmi.list = MagicMock(return_value=[])
        instance.power_status = MagicMock(return_value=True)

        with pytest.raises(LookupError, message="ipmi instance should not be present") as excinfo:
            instance.validate()
        if "ipmi client" not in str(excinfo.value):
            pytest.fail("Received unexpected error message for missing ipmi instance: %s" % str(excinfo.value))

    @mock.patch.object(j.clients, '_ipmi')
    @mock.patch.object(j.clients, '_zboot')
    def test_install(self, zboot, ipmi):
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)
        instance._network.hosts.list = MagicMock(return_value=[])
        ipmi.get().power_status = MagicMock(return_value="on")

        instance.install()

        instance._network.hosts.add.assert_called_with(
            self._valid_data['mac'], self._valid_data['ip'], self._valid_data['hostname'])
        instance._host.configure_ipxe_boot.assert_called_with(self._valid_data['lkrnUrl'])

        # state check should pass
        instance.state.check('actions', 'install', 'ok')

    @mock.patch.object(j.clients, '_zboot')
    def test_uninstall(self, zboot):
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)
        instance.state.set('actions', 'install', 'ok')

        instance.uninstall()

        instance._network.hosts.remove.assert_called_with(self._valid_data['hostname'])

        with pytest.raises(StateCheckError, message="install action state check should fail"):
            instance.state.check('actions', 'install', 'ok')

    @mock.patch.object(j.clients, '_ipmi')
    @mock.patch.object(j.clients, '_zboot')
    def test_power_on_not_installed(self, zboot, ipmi):
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)
        with pytest.raises(StateCheckError, message="power_on should be not be able to be called before install"):
            instance.power_on()

    @mock.patch.object(j.clients, '_ipmi')
    @mock.patch.object(j.clients, '_zboot')
    def test_power_on(self, zboot, ipmi):
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)
        instance.state.set('actions', 'install', 'ok')

        instance.power_on()
        ipmi.get().power_on.assert_called_with()

        # check if instance power state True
        assert instance.data['powerState']

    @mock.patch.object(j.clients, '_ipmi')
    @mock.patch.object(j.clients, '_zboot')
    def test_power_off_not_installed(self, zboot, ipmi):
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)
        with pytest.raises(StateCheckError, message="power_off should be not be able to be called before install"):
            instance.power_off()

    @mock.patch.object(j.clients, '_ipmi')
    @mock.patch.object(j.clients, '_zboot')
    def test_power_off(self, zboot, ipmi):
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)
        instance.state.set('actions', 'install', 'ok')

        instance.power_off()
        ipmi.get().power_off.assert_called_with()

        # check if instance power state False
        assert not instance.data['powerState']

    @mock.patch.object(j.clients, '_ipmi')
    @mock.patch.object(j.clients, '_zboot')
    def test_power_cycle_not_installed(self, zboot, ipmi):
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)
        with pytest.raises(StateCheckError, message="power_cycle should be not be able to be called before install"):
            instance.power_cycle()

    @mock.patch.object(j.clients, '_ipmi')
    @mock.patch.object(j.clients, '_zboot')
    def test_power_cycle(self, zboot, ipmi):
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)
        instance.state.set('actions', 'install', 'ok')

        instance.power_cycle()
        ipmi.get().power_cycle.assert_called_with()

    @mock.patch.object(j.clients, '_ipmi')
    @mock.patch.object(j.clients, '_zboot')
    def test_power_status_not_installed(self, zboot, ipmi):
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)
        with pytest.raises(StateCheckError, message="power_status should be not be able to be called before install"):
            instance.power_status()

    @mock.patch.object(j.clients, '_ipmi')
    @mock.patch.object(j.clients, '_zboot')
    def test_power_status(self, zboot, ipmi):
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)
        instance.state.set('actions', 'install', 'ok')
        ipmi.get().power_status = MagicMock(return_value="on")

        status = instance.power_status()

        assert status == True

        ipmi.get().power_status = MagicMock(return_value="off")
        status = instance.power_status()

        assert status == False

    def test_monitor_not_installed(self):
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)
        with pytest.raises(StateCheckError, message="monitor should be not be able to be called before install"):
            instance.monitor()

    def test_monitor_matching_state(self):
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)
        instance.state.set('actions', 'install', 'ok')
        instance.power_on = MagicMock()
        instance.power_off = MagicMock()
        instance.power_status = MagicMock(return_value=True)
        instance.data['powerState'] = True

        instance.monitor()

        # no power calls should be make
        instance.power_on.assert_not_called()
        instance.power_off.assert_not_called()

    def test_monitor_power_on(self):
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)
        instance.state.set('actions', 'install', 'ok')
        instance.power_on = MagicMock()
        instance.power_off = MagicMock()
        instance.power_status = MagicMock(return_value=False)
        instance.data['powerState'] = True

        instance.monitor()

        # power state mismatched, power_on should have been called
        instance.power_on.assert_called_with()
        instance.power_off.assert_not_called()

    def test_monitor_power_off(self):
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)
        instance.state.set('actions', 'install', 'ok')
        instance.power_on = MagicMock()
        instance.power_off = MagicMock()
        instance.power_status = MagicMock(return_value=True)
        instance.data['powerState'] = False

        instance.monitor()

        # power state mismatched, power_off should have been called
        instance.power_on.assert_not_called()
        instance.power_off.assert_called_with()

    @mock.patch.object(j.clients, '_zboot')
    def test_configure_ipxe_boot_not_installed(self, zboot):
        boot_url = "some.url"
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)
        with pytest.raises(StateCheckError, message="monitor should be not be able to be called before install"):
            instance.configure_ipxe_boot(boot_url)

    @mock.patch.object(j.clients, '_zboot')
    def test_configure_ipxe_boot(self, zboot):
        boot_url = "some.url"
        instance = ZerobootIpmiHost(name="test", data=self._valid_data)
        instance.state.set('actions', 'install', 'ok')

        # call with same ipxe URL as set in data
        instance.configure_ipxe_boot(self._valid_data["lkrnUrl"])
        instance._host.configure_ipxe_boot.assert_not_called()

        # call with difference ipxe URL as set in data
        instance.configure_ipxe_boot(boot_url)
        instance._host.configure_ipxe_boot.assert_called_with(boot_url)

        assert instance.data["lkrnUrl"] == boot_url
