#!/usr/bin/env python

from qatrfm.environment import TerraformEnv
from qatrfm.testcase import TrfmTestCase


class TestCase1(TrfmTestCase):
    def run(self):
        # test logic here
        self.logger.info('Running test case {}'.format(self.name))
        domains = self.env.get_domains()
        domains[0].execute_cmd('ping -c 1 {}'.format(domains[1].ip))
        

class TestCase2(TrfmTestCase):
    def run(self):
        # test logic here
        self.logger.info('Run test case {}'.format(self.name))
        domains = self.env.get_domains()
        domains[1].execute_cmd('ping -c 1 {}'.format(domains[0].ip))



def main():
    tf_file = '/home/jlausuch/Documents/repos/qa-terraform-lib/tests/example/test.tf'

    env = TerraformEnv(tf_file)
    env.deploy()

    try:
        test1 = TestCase1(env, 'test 1', 'ping from VM1 to VM2')
        test1.run()

        env.reset()

        test2 = TestCase2(env, 'test 2', 'ping from VM2 to VM1')
        test2.run()
    except Exception as e:
        logger.error("Something went wrong:\n{}".format(e))
        env.clean()    

    env.clean()
    

if __name__ == "__main__":
    main()
