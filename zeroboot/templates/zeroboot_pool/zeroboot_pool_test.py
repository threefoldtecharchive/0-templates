import os
import pytest
from unittest import TestCase
from unittest.mock import MagicMock

from js9 import j
from zerorobot.template.state import StateCheckError

from JumpScale9Zrobot.test.utils import ZrobotBaseTest
from zeroboot_pool import ZerobootPool

class TestZerobootPoolTemplate(ZrobotBaseTest):
    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), ZerobootPool)

    def test_valid_host_validation(self):
        pool = ZerobootPool(name="test")
        # mock racktivity host service
        pool.api.services.get = MagicMock(return_value=MagicMock(template_uid="github.com/zero-os/0-boot-templates/zeroboot_racktivity_host/0.0.1"))
        pool.api.services.get().state.check = MagicMock(return_value=None)

        pool._validate_host("test_host_instance")

    def test_host_validation_invalid_template(self):
        pool = ZerobootPool(name="test")
        # mock racktivity host service
        pool.api.services.get = MagicMock(return_value=MagicMock(template_uid="github.com/zero-os/0-boot-templates/a_random_template/0.0.1"))
        pool.api.services.get().state.check = MagicMock(return_value=None)

        with pytest.raises(RuntimeError, message="Invalid template should raise RuntimeError"):
            pool._validate_host("test_host_instance")

    def test_host_validation_failed_state_check(self):
        pool = ZerobootPool(name="test")
        # mock racktivity host service
        pool.api.services.get = MagicMock(return_value=MagicMock(template_uid="github.com/zero-os/0-boot-templates/zeroboot_racktivity_host/0.0.1"))
        pool.api.services.get().state.check = MagicMock(side_effect=StateCheckError("state check failed"))

        with pytest.raises(StateCheckError, message="Uninstalled host should raise StateCheckError"):
            pool._validate_host("test_host_instance")

    def test_valid_hosts(self):
        pool = ZerobootPool(name="test", data={"zerobootHosts": ["host1", "host2"]})
        pool._validate_host = MagicMock()

        pool.validate()

    def test_validation_duplicate_hosts(self):
        # data contains duplicate hosts
        pool = ZerobootPool(name="test", data={"zerobootHosts": ["host1", "host2", "host1"]})
        pool._validate_host = MagicMock()

        with pytest.raises(ValueError, message="invalid data should contain duplicate host names"):
            pool.validate()

    def test_add(self):
        pool = ZerobootPool(name="test", data={"zerobootHosts": ["host1", "host2"]})
        pool._validate_host = MagicMock()

        # add new host
        pool.add("host3")

        assert len(pool.data.get("zerobootHosts")) == 3

        # add another
        pool.add("host4")

        assert len(pool.data.get("zerobootHosts")) == 4

    def test_remove(self):
        pool = ZerobootPool(name="test", data={"zerobootHosts": ["host1", "host2", "host3"]})
        pool._validate_host = MagicMock()

         # remove host
        pool.remove("host3")

        assert len(pool.data.get("zerobootHosts")) == 2

        # empty pool
        pool.remove("host1")
        assert len(pool.data.get("zerobootHosts")) == 1
        pool.remove("host2")
        assert len(pool.data.get("zerobootHosts")) == 0

    def test_remove_nonexisting_host(self):
        pool = ZerobootPool(name="test", data={"zerobootHosts": ["host1", "host2", "host3"]})
        pool._validate_host = MagicMock()

        # remove non existing host
        pool.remove("ghost_host")

        assert len(pool.data.get("zerobootHosts")) == 3

        # remove a host and try get a ghost again
        pool.remove("host3")
        pool.remove("ghost_host")

        assert len(pool.data.get("zerobootHosts")) == 2

        # add a host and try get a ghost again
        pool.add("host3")
        pool.remove("ghost_host")

        assert len(pool.data.get("zerobootHosts")) == 3

        # empty list and try get a ghost again
        pool.remove("host1")
        pool.remove("host2")
        pool.remove("host3")
        pool.remove("ghost_host")

        assert len(pool.data.get("zerobootHosts")) == 0

    def test_add_duplicate(self):
        pool = ZerobootPool(name="test", data={"zerobootHosts": ["host1", "host2"]})
        pool._validate_host = MagicMock()

        # add already existing host
        with pytest.raises(ValueError, message="Adding already present host should raise ValueError"):
            pool.add("host1")

    def test_unreserved_host(self):
        hosts = ["host1", "host2"]
        pool = ZerobootPool(name="test", data={"zerobootHosts": hosts})
        pool._validate_host = MagicMock()
        pool.api = MagicMock()

        # request unreserved host, check if host is in hosts list
        r1 = pool.unreserved_host("r1-guid")

        if r1 not in hosts:
            pytest.fail("Returned host was not in set hosts list")

        # mock first reservation
        mock_res1 = MagicMock()
        mock_res1.schedule_action().wait().result = r1
        pool.api.services.find = MagicMock(return_value=[mock_res1])

        # request another unreserved host, check if host is in hosts list and is not the first host
        r2 = pool.unreserved_host("r2-guid")

        if r2 not in hosts:
            pytest.fail("Returned host was not in set hosts list")
        
        if r1 == r2:
            pytest.fail("Different reservations can not be of the same host: reservation1:'%s'; reservation2:'%s'" % (r1, r2))

        # mock second reservation
        mock_res1 = MagicMock()
        mock_res1.schedule_action().wait().result = r1
        mock_res2 = MagicMock()
        mock_res2.schedule_action().wait().result = r2
        pool.api.services.find = MagicMock(return_value=[mock_res1, mock_res2])

        # there are only 2 available hosts, third reservation should fail
        with pytest.raises(ValueError, message="There should not be any free hosts left, thus unreserved_host will raise a ValueError"):
            r3 = pool.unreserved_host("r3-guid")
