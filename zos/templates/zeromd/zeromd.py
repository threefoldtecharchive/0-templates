from js9 import j

from zerorobot.template.base import TemplateBase


class Zeromd(TemplateBase):
    version = '0.0.1'
    template_name = "zeromd"

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)
