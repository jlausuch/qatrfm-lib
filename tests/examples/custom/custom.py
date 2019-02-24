#!/usr/bin/env python

from qatrfm.testcase import TrfmTestCase
from qatrfm.utils.logger import QaTrfmLogger

logger = QaTrfmLogger.getQatrfmLogger(__name__)


class CustomTest(TrfmTestCase):

    def __init__(self, env, name):
        description = "Example using a custom .tf file"
        super(CustomTest, self).__init__(env, name, description)

    def run(self):
        self.logger.info('Running test case {}'.format(self.name))
        vm = self.env.domains[0]
        [retcode, output] = vm.execute_cmd('ip address show')
        return self.EX_OK
