#!/usr/bin/env python3

from qatrfm.testcase import TrfmTestCase
from qatrfm.utils.logger import QaTrfmLogger

logger = QaTrfmLogger.getQatrfmLogger(__name__)


class SimpleTest(TrfmTestCase):

    def __init__(self, env, name):
        description = "Example how to transfer files from/to VMs"
        super(SimpleTest, self).__init__(env, name, description)

    def run(self):

        vm1 = self.env.domains[0]
        vm1.transfer_file(remote_file_path='/etc/resolv.conf',
                          local_file_path='/root/test.resolv.conf',
                          type='get')
        return self.EX_OK
