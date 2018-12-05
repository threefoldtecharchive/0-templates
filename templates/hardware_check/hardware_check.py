from Jumpscale import j

from zerorobot.template.base import TemplateBase

from http.client import HTTPSConnection


class HardwareCheck(TemplateBase):

    version = '0.0.1'
    template_name = 'hardware_check'

    def __init__(self, name=None, guid=None, data=None):
        super().__init__(name=name, guid=guid, data=data)

    def validate(self):
        for param in ['botToken', 'chatId', 'supported']:
            if not self.data[param]:
                raise ValueError("parameter '%s' not valid: %s" % (param, str(self.data[param])))

        for supported in self.data['supported']:
            for param in ['ssdCount', 'hddCount', 'ram', 'cpu', 'name']:
                if not supported.get(param):
                    raise ValueError("parameter '%s' not valid: %s" % (param, str(supported.get(param))))

    def _get_bot_client(self):
        data = {
            'bot_token_': self.data['botToken'],
        }
        # make sure the config exists
        cl = j.clients.telegram_bot.get(
            instance=self.guid,
            data=data,
            create=True,
            die=True)

        # update the config with correct value
        cl.config.data.update(data)
        cl.config.save()

        return cl

    def _disk(self, cl):
        ssd_count = 0
        hdd_count = 0

        for disk in cl.disk.list()['blockdevices']:
            # ignore the boot usb drive
            if disk.get('tran') == 'usb':
                continue

            # check disk type
            if disk.get('rota') == '1':
                hdd_count += 1
            else:
                ssd_count += 1

            # do drive test
            name = disk.get('name')
            num_sectors = int(disk.get('size')) // int(disk.get('phy-sec'))
            test_sectors = [1, num_sectors // 2, num_sectors - 1]

            cl.bash('echo test > /test')
            for sector in test_sectors:
                # write to sector
                cmd = 'dd if=/test of=/dev/{} seek={}'.format(name, sector)
                cl.system(cmd).get()
                # read from sector
                cmd = 'dd if=/dev/{} bs=1 count=4 skip={}'.format(
                    name, sector * 512)
                result = cl.system(cmd).get().stdout
                if result != 'test\n':
                    raise j.exceptions.RuntimeError(
                        "Hardwaretest drive /dev/{} failed.".format(name))

        return hdd_count, ssd_count

    def _ram(self, cl):
        ram = cl.info.mem().get('total')
        ram_mib = ram // 1024 // 1024
        return ram_mib

    def _cpu(self, cl):
        cpu = cl.info.cpu()[0].get('modelName').split()[2]
        return cpu

    def check(self, node_name):
        cl = j.clients.zos.get(instance=node_name)
        message = "Node with id {} has completed the hardwarecheck successfully.".format(
            node_name)

        try:
            hdd, ssd = self._disk(cl)
            ram = self._ram(cl)
            cpu = self._cpu(cl)

            for supported in self.data['supported']:
                if ram < supported['ram'] - 5:
                    continue

                if cpu != supported['cpu']:
                    continue

                if hdd != supported['hddCount']:
                    continue

                if ssd != supported['ssdCount']:
                    continue
                break
            else:
                raise j.exceptions.RuntimeError(
                    "No supported hardware combination for ram={}MiB ssd={} hdd={} cpu={}".format(ram, ssd, hdd, cpu))

            self.logger.info("Hardware check succeeded")
        except Exception as err:
            message = "Node with id {} has failed the hardwarecheck: {}".format(
                node_name, str(err))
            raise j.exceptions.RuntimeError(message)
        finally:
            bot_cl = self._get_bot_client()
            bot_cl.send_message(self.data['chatId'], message)

