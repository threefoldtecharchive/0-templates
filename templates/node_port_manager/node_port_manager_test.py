pass
# import os
# from unittest.mock import MagicMock, patch

# import pytest
# from JumpscaleZrobot.test.utils import ZrobotBaseTest, mock_decorator
# from node_port_manager import NODE_CLIENT, NodePortManager
# from zerorobot.template.state import StateCheckError

# import itertools


# class TestNodePortManagerTemplate(ZrobotBaseTest):

#     @classmethod
#     def setUpClass(cls):
#         super().preTest(os.path.dirname(__file__), NodePortManager)

#     def setUp(self):
#         patch('jumpscale.j.clients', MagicMock()).start()

#     def tearDown(self):
#         patch.stopall()

#     def test_reserve(self):
#         node_sal = MagicMock()

#         def freeports(nrports=1):
#             import itertools
#             i = 0

#             def f():
#                 while True:
#                     yield i
#                     i += 1
#             iter = f()
#             return list(itertools.islice(iter, nrports))

#         node_sal.freeports = freeports
#         # get_node = patch('jumpscale.j.clients.zos.get', MagicMock(return_value=node_sal)).start()
#         mgr = NodePortManager(name="name")
