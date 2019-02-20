#!/usr/bin/env python

import sys

from qatrfm.environment import TerraformEnv
from qatrfm.testcase import TrfmTestCase


class MyTestCase(TrfmTestCase):
    def run(self):
        # test logic here
        self.logger.info('Running test case {}'.format(self.name))
        vm1 = self.env.domains[0]
        vm2 = self.env.domains[1]
        [retcode, output] = vm1.execute_cmd('ping -c 1 {}'.format(vm2.ip))
        return self.EX_OK


def main():

    env = TerraformEnv(num_domains=2)
    env.deploy()
    exit_status = TrfmTestCase.EX_OK

    try:
        test = MyTestCase(env, 'test', 'simple ping from VM1 to VM2')
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
