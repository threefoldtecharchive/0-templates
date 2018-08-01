import os
import pytest
from unittest import mock
from unittest.mock import MagicMock

from js9 import j
from zerorobot.template.state import StateCheckError

from JumpScale9Zrobot.test.utils import ZrobotBaseTest
from zeroboot_racktivity_host import ZerobootRacktivityHost

class TestZerobootRacktivityHostTemplate(ZrobotBaseTest):
    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), ZerobootRacktivityHost)
        cls._valid_data = {
            'zerobootClient': 'zboot1-zb',
            'racktivities': [
                {
                'client': 'zboot1-rack',
                'port': 6,
                'powermodule': 'P1',
                },
                {
                'client': 'zboot1-rack',
                'port': 7,
                'powermodule': 'P1',
                },
            ],
            'mac': 'well:this:a:weird:mac:address',
            'ip': '10.10.1.1',
            'network': '10.10.1.0/24',
            'hostname': 'test-01',
            'lkrnUrl': 'some.ixpe.url',
        }

    @property
    def _rack_clients(self):
        """ Returns the racktivity clients defined in self._valid_data

        used for mocking
        
        Returns:
            [string] -- List of Rackitivity clients in self._valid_data
        """
        racktivity_clients = []
        for d in self._valid_data['racktivities']:
            racktivity_clients.append(d['client'])

        return racktivity_clients

    @mock.patch.object(j.clients, '_racktivity')
    @mock.patch.object(j.clients, '_zboot')
    def test_validation_valid_data(self, zboot, rack):
        zboot.list = MagicMock(return_value=[self._valid_data['zerobootClient']])
        rack.list = MagicMock(return_value=self._rack_clients)

        _ = ZerobootRacktivityHost(name="test", data=self._valid_data)

    @mock.patch.object(j.clients, '_racktivity')
    @mock.patch.object(j.clients, '_zboot')
    def test_validation_required_fields(self, zboot, rack):
        zboot.list = MagicMock(return_value=[self._valid_data['zerobootClient']])
        rack.list = MagicMock(return_value=self._rack_clients)

        test_cases = [
            {
                'data': {
                    'racktivities': [
                        {
                        'client': 'zboot1-rack',
                        'port': 6,
                        'powermodule': 'P1',
                        },
                        {
                        'client': 'zboot1-rack',
                        'port': 7,
                        'powermodule': 'P1',
                        },
                    ],
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
                'message': "Should fail: missing racktivities",
                'missing': 'racktivities',
            },
            {
                'data': {
                    'zerobootClient': 'zboot1-zb',
                    'racktivities': [
                        {
                        'client': 'zboot1-rack',
                        'port': 6,
                        'powermodule': 'P1',
                        },
                        {
                        'client': 'zboot1-rack',
                        'port': 7,
                        'powermodule': 'P1',
                        },
                    ],
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
                    'racktivities': [
                        {
                        'client': 'zboot1-rack',
                        'port': 6,
                        'powermodule': 'P1',
                        },
                        {
                        'client': 'zboot1-rack',
                        'port': 7,
                        'powermodule': 'P1',
                        },
                    ],
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
                    'racktivities': [
                        {
                        'client': 'zboot1-rack',
                        'port': 6,
                        'powermodule': 'P1',
                        },
                        {
                        'client': 'zboot1-rack',
                        'port': 7,
                        'powermodule': 'P1',
                        },
                    ],
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
                    'racktivities': [
                        {
                        'client': 'zboot1-rack',
                        'port': 6,
                        'powermodule': 'P1',
                        },
                        {
                        'client': 'zboot1-rack',
                        'port': 7,
                        'powermodule': 'P1',
                        },
                    ],
                    'network': '10.10.1.0/24',
                    'mac': 'well:this:a:weird:mac:address',
                    'hostname': 'test-01',
                },
                'message': "Should fail: missing ip address",
                'missing': 'ip',
            },
        ]

        for tc in test_cases:
            instance = ZerobootRacktivityHost(name="test", data=tc['data'])

            with pytest.raises(
                    ValueError, message="Unexpected success: %s\n\nData: %s" %(tc['message'], tc['data'])) as excinfo:
                instance.validate()
            
            if tc['missing'] not in str(excinfo):
                pytest.fail(
                    "Error message did not contain missing field('%s'): %s" % (tc['missing'], str(excinfo)))

    @mock.patch.object(j.clients, '_racktivity')
    @mock.patch.object(j.clients, '_zboot')
    def test_invalid_racktivity_port(self, zboot, rack):
        zboot.list = MagicMock(return_value=[self._valid_data['zerobootClient']])
        rack.list = MagicMock(return_value=self._rack_clients)

        data = {
            'zerobootClient': 'zboot1-zb',
            'racktivities': [
                {
                'client': 'zboot1-rack',
                'powermodule': 'P1',
                },
            ],
            'mac': 'well:this:a:weird:mac:address',
            'ip': '10.10.1.1',
            'network': '10.10.1.0/24',
            'hostname': 'test-01',
            'lkrnUrl': 'some.ixpe.url',
        }
        instance = ZerobootRacktivityHost(name="test", data=data)

        with pytest.raises(ValueError, message="Should fail due to missing racktivity port"):
            instance.validate()

        data = {
            'zerobootClient': 'zboot1-zb',
            'racktivities': [
                {
                'client': 'zboot1-rack',
                'port': 'FOO',
                'powermodule': 'P1',
                },
            ],
            'mac': 'well:this:a:weird:mac:address',
            'ip': '10.10.1.1',
            'network': '10.10.1.0/24',
            'hostname': 'test-01',
            'lkrnUrl': 'some.ixpe.url',
        }
        instance = ZerobootRacktivityHost(name="test", data=data)

        with pytest.raises(ValueError, message="Should fail due to invalid racktivity port"):
            instance.validate()

    @mock.patch.object(j.clients, '_racktivity')
    @mock.patch.object(j.clients, '_zboot')
    def test_validate_no_zboot_instance(self, zboot, rack):
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)

        zboot.list = MagicMock(return_value=[])
        rack.list = MagicMock(return_value=self._rack_clients)
        instance.power_status = MagicMock(return_value=True)

        with pytest.raises(LookupError, message="zeroboot instance should not be present") as excinfo:
            instance.validate()
        if "zboot client" not in str(excinfo.value):
            pytest.fail("Received unexpected error message for missing zboot instance: %s" % str(excinfo.value))

    @mock.patch.object(j.clients, '_racktivity')
    @mock.patch.object(j.clients, '_zboot')
    def test_validate_no_racktivity_instance(self, zboot, rack):
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)

        zboot.list = MagicMock(return_value=[self._valid_data['zerobootClient']])
        rack.list = MagicMock(return_value=[])
        instance.power_status = MagicMock(return_value=True)

        with pytest.raises(LookupError, message="racktivity instance should not be present") as excinfo:
            instance.validate()
        if "racktivity client" not in str(excinfo.value):
            pytest.fail("Received unexpected error message for missing racktivity instance: %s" % str(excinfo.value))

    @mock.patch.object(j.clients, '_racktivity')
    @mock.patch.object(j.clients, '_zboot')
    def test_install(self, zboot, rack):
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)
        instance._network.hosts.list = MagicMock(return_value=[])

        instance.install()

        instance._network.hosts.add.assert_called_with(
            self._valid_data['mac'], self._valid_data['ip'], self._valid_data['hostname'])
        instance._host.configure_ipxe_boot.assert_called_with(self._valid_data['lkrnUrl'])

        # state check should pass
        instance.state.check('actions', 'install', 'ok')

    @mock.patch.object(j.clients, '_zboot')
    def test_uninstall(self, zboot):
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)
        instance.state.set('actions', 'install', 'ok')

        instance.uninstall()

        instance._network.hosts.remove.assert_called_with(self._valid_data['hostname'])

        with pytest.raises(StateCheckError, message="install action state check should fail"):
            instance.state.check('actions', 'install', 'ok')

    @mock.patch.object(j.clients, '_racktivity')
    @mock.patch.object(j.clients, '_zboot')
    def test_power_on_not_installed(self, zboot, rack):
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)
        with pytest.raises(StateCheckError, message="power_on should be not be able to be called before install"):
            instance.power_on()

    @mock.patch.object(j.clients, '_racktivity')
    @mock.patch.object(j.clients, '_zboot')
    def test_power_on(self, zboot, rack):
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)
        instance.state.set('actions', 'install', 'ok')
        rack.get = MagicMock()

        instance.power_on()

        expected_calls = []
        for d in reversed(self._valid_data['racktivities']):
            expected_calls.append(zboot.get().port_power_on(d['port'], mock.ANY, d['powermodule']))

        # check if instance power state True
        assert instance.data['powerState']

    @mock.patch.object(j.clients, '_racktivity')
    @mock.patch.object(j.clients, '_zboot')
    def test_power_off_not_installed(self, zboot, rack):
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)
        with pytest.raises(StateCheckError, message="power_off should be not be able to be called before install"):
            instance.power_off()

    @mock.patch.object(j.clients, '_racktivity')
    @mock.patch.object(j.clients, '_zboot')
    def test_power_off(self, zboot, rack):
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)
        instance.state.set('actions', 'install', 'ok')
        rack.get = MagicMock()

        instance.power_off()

        expected_calls = []
        for d in reversed(self._valid_data['racktivities']):
            expected_calls.append(zboot.get().port_power_off(d['port'], mock.ANY, d['powermodule']))

        # check if instance power state False
        assert not instance.data['powerState']

    @mock.patch.object(j.clients, '_racktivity')
    @mock.patch.object(j.clients, '_zboot')
    def test_power_cycle_not_installed(self, zboot, rack):
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)
        with pytest.raises(StateCheckError, message="power_cycle should be not be able to be called before install"):
            instance.power_cycle()

    @mock.patch.object(j.clients, '_racktivity')
    @mock.patch.object(j.clients, '_zboot')
    def test_power_cycle(self, zboot, rack):
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)
        instance.state.set('actions', 'install', 'ok')
        rack.get = MagicMock()

        instance.power_cycle()

        expected_calls = []
        for d in reversed(self._valid_data['racktivities']):
            expected_calls.append(zboot.get().port_power_cycle(d['port'], mock.ANY, d['powermodule']))

    @mock.patch.object(j.clients, '_racktivity')
    @mock.patch.object(j.clients, '_zboot')
    def test_power_status_not_installed(self, zboot, rack):
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)
        with pytest.raises(StateCheckError, message="power_status should be not be able to be called before install"):
            instance.power_status()

    @mock.patch.object(j.clients, '_racktivity')
    @mock.patch.object(j.clients, '_zboot')
    def test_power_status(self, zboot, rack):
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)
        instance.state.set('actions', 'install', 'ok')
        rack.get = MagicMock()

        instance.power_status()

        expected_calls = []
        for d in reversed(self._valid_data['racktivities']):
            expected_calls.append(zboot.get().port_info(d['port'], mock.ANY, d['powermodule']))


    def test_monitor_not_installed(self):
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)
        with pytest.raises(StateCheckError, message="monitor should be not be able to be called before install"):
            instance.monitor()

    def test_monitor_matching_state(self):
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)
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
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)
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
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)
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
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)

        with pytest.raises(StateCheckError, message="monitor should be not be able to be called before install"):
            instance.configure_ipxe_boot(boot_url)

    @mock.patch.object(j.clients, '_zboot')
    def test_configure_ipxe_boot(self, zboot):
        boot_url = "some.url"
        instance = ZerobootRacktivityHost(name="test", data=self._valid_data)
        instance.state.set('actions', 'install', 'ok')

        # call with same ipxe URL as set in data
        instance.configure_ipxe_boot(self._valid_data["lkrnUrl"])
        instance._host.configure_ipxe_boot.assert_not_called()

        # call with difference ipxe URL as set in data
        instance.configure_ipxe_boot(boot_url)
        instance._host.configure_ipxe_boot.assert_called_with(boot_url)

        assert instance.data["lkrnUrl"] == boot_url
