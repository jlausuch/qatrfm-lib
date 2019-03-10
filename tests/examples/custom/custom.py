#!/usr/bin/env python3

from qatrfm.testcase import TrfmTestCase
from qatrfm.utils.logger import QaTrfmLogger

logger = QaTrfmLogger.getQatrfmLogger(__name__)

""" Custom test example

This example test shows how to use a custom .tf file for Terraform.
The .tf file should be placed in the same directory as this python file
and the library will detect it and use it.

For custom .tf files, it is important keep using the 2 variables
'net_octet' and 'basename'. Otherwise, it losses the capability of this tool
to create isolation between other concurrent tests.

The 2 networks are created using the range 10.X.Y.0/24.
The second octet (X) is calculated using variable net_octet and this allows
having the third octet (Y) customizable up to 255 possible networks for
the environment.

The example custom .tf file also creates 2 domains with different images
defined by 2 input variables "image1" and "image2"

"""


class CustomTest(TrfmTestCase):

    def __init__(self, env, name):
        description = "Example using a custom .tf file"
        super(CustomTest, self).__init__(env, name, description)

    def run(self):
        self.logger.info('Running test case {}'.format(self.name))
        vm1 = self.env.domains[0]
        vm2 = self.env.domains[1]
        vm1.execute_cmd('ip address show')
        vm1.execute_cmd('cat /etc/os-release')
        vm2.execute_cmd('ip address show')
        vm2.execute_cmd('cat /etc/os-release')
        return self.EX_OK
