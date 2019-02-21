#!/usr/bin/env python

import sys

from qatrfm.environment import TerraformEnv
from qatrfm.testcase import TrfmTestCase
from qatrfm.utils.logger import QaTrfmLogger

logger = QaTrfmLogger.getQatrfmLogger(__name__)


class MyTestCase(TrfmTestCase):
    def run(self):
        # test logic here
        self.logger.info("Running test case '{}' ...".format(self.name))
        vm1 = self.env.domains[0]
        vm1.transfer_file(remote_file_path='/etc/resolv.conf',
                          local_file_path='/root/test.resolv.conf',
                          type='get')
        return self.EX_OK


def main():
    hdd = ("/var/lib/libvirt/images/my_image.qcow2")
    env = TerraformEnv(image=hdd, num_domains=1)
    env.deploy()
    exit_status = TrfmTestCase.EX_OK

    try:
        test = MyTestCase(env, 'simple_test', 'Create a VM and transfer files')
        if (test.run() != TrfmTestCase.EX_OK):
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
