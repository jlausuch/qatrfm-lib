#!/usr/bin/env python

from qatrfm.testcase import TrfmTestCase

from qatrfm.utils.logger import QaTrfmLogger

logger = QaTrfmLogger.getQatrfmLogger(__name__)


class TestCase1(TrfmTestCase):
    def __init__(self, env, name):
        description = "Example Multitest test 1. Ping from VM1 to VM2"
        super(TestCase1, self).__init__(env, name, description)

    def run(self):
        vm1 = self.env.domains[0]
        vm2 = self.env.domains[1]
        [retcode, output] = vm1.execute_cmd('ping -c 1 {}'.format(vm2.ip))
        self.env.reset()
        if (retcode == 0):
            return self.EX_OK
        else:
            return self.EX_RUN_ERROR


class TestCase2(TrfmTestCase):
    def __init__(self, env, name):
        description = "Example Multitest test 2. Ping from VM2 to VM1"
        super(TestCase2, self).__init__(env, name, description)

    def run(self):
        vm1 = self.env.domains[0]
        vm2 = self.env.domains[1]
        [retcode, output] = vm2.execute_cmd('ping -c 1 {}'.format(vm1.ip))
        if (retcode == 0):
            return self.EX_OK
        else:
            return self.EX_RUN_ERROR
