from unittest.mock import MagicMock, patch
import os

from bridge import Bridge, NODE_CLIENT
from zerorobot.template.state import StateCheckError

from JumpscaleZrobot.test.utils import ZrobotBaseTest, mock_decorator

patch("gevent.sleep", MagicMock()).start()


class TestBridgeTemplate(ZrobotBaseTest):

    @classmethod
    def setUpClass(cls):
        super().preTest(os.path.dirname(__file__), Bridge)

    def setUp(self):
        patch('jumpscale.j.clients', MagicMock()).start()

    def tearDown(self):
        patch.stopall()

