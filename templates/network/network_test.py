from unittest.mock import MagicMock, patch
import os

from network import Network, NODE_CLIENT
from zerorobot.template.state import StateCheckError

from JumpscaleZrobot.test.utils import ZrobotBaseTest, mock_decorator

patch("gevent.sleep", MagicMock()).start()


class TestNetworkTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), Network)

    def setUp(self):
        patch('jumpscale.j.clients', MagicMock()).start()

    def tearDown(self):
        patch.stopall()

