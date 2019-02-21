#!/usr/bin/env python

import sys

from qatrfm.environment import TerraformEnv
from qatrfm.testcase import TrfmTestCase

from qatrfm.utils.logger import QaTrfmLogger

logger = QaTrfmLogger.getQatrfmLogger(__name__)


class TestCase1(TrfmTestCase):
    def run(self):
        # test logic here
        self.logger.info('Running test case {}'.format(self.name))
        vm1 = self.env.domains[0]
        vm2 = self.env.domains[1]
        [retcode, output] = vm1.execute_cmd('ping -c 1 {}'.format(vm2.ip))
        if (retcode == 0):
            return self.EX_OK
        else:
            return self.EX_RUN_ERROR


class TestCase2(TrfmTestCase):
    def run(self):
        # test logic here
        self.logger.info('Run test case {}'.format(self.name))
        vm1 = self.env.domains[0]
        vm2 = self.env.domains[1]
        [retcode, output] = vm2.execute_cmd('ping -c 1 {}'.format(vm1.ip))
        if (retcode == 0):
            return self.EX_OK
        else:
            return self.EX_RUN_ERROR


def main():
    hdd = ("/var/lib/libvirt/images/my_image.qcow2")
    env = TerraformEnv(image=hdd, num_domains=2, snapshots=True)
    env.deploy()
    exit_status = TrfmTestCase.EX_OK

    try:
        test1 = TestCase1(env, 'test 1', 'ping from VM1 to VM2')
        if (test1.run() != TrfmTestCase.EX_OK):
            exit_status = TrfmTestCase.EX_RUN_ERROR

        env.reset()

        test2 = TestCase2(env, 'test 2', 'ping from VM2 to VM1')
        if (test2.run() != TrfmTestCase.EX_OK):
            exit_status = TrfmTestCase.EX_RUN_ERROR

    except Exception as e:
        logger.error("Something went wrong:\n{}".format(e))
        env.clean()
        sys.exit(TrfmTestCase.EX_RUN_ERROR)

    env.clean()
    logger.info("The test finished with status={}".format(exit_status))
    sys.exit(exit_status)


if __name__ == "__main__":
    main()
