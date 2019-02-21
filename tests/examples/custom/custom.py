#!/usr/bin/env python

import os
import sys

from qatrfm.environment import TerraformEnv
from qatrfm.testcase import TrfmTestCase


class MyTestCase(TrfmTestCase):
    def run(self):
        # test logic here
        self.logger.info('Running test case {}'.format(self.name))
        vm = self.env.domains[0]
        [retcode, output] = vm.execute_cmd('ip address show')
        return self.EX_OK


def main():
    hdd = ("/var/lib/libvirt/images/my_image.qcow2")
    path = os.path.dirname(os.path.realpath(__file__))
    tf_file = ("{}/{}".format(path, 'custom.tf'))

    env = TerraformEnv(image=hdd, tf_file=tf_file, num_domains=1)
    env.deploy()
    exit_status = TrfmTestCase.EX_OK

    try:
        test = MyTestCase(env, 'test', 'Test case with custom TF file')
        if (test.run() != TrfmTestCase.EX_OK):
            exit_status = TrfmTestCase.EX_RUN_ERROR

    except Exception as e:
        print("Something went wrong:\n{}".format(e))
        env.clean()
        sys.exit(TrfmTestCase.EX_RUN_ERROR)

    env.clean()
    print("The test finished with status={}".format(exit_status))
    sys.exit(exit_status)


if __name__ == "__main__":
    main()
