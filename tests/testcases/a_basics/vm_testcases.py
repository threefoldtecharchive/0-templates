from tests.testcases.base_test import BaseTest


class TESTVM(BaseTest):
    def test001_install_vm_with_default_params(self):
        self.controller.vm_manager.install(wait=True)
