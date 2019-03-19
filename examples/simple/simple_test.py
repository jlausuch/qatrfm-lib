#!/usr/bin/env python3

import os
from pathlib import Path

from qatrfm.testcase import TrfmTestCase
from qatrfm.utils.logger import QaTrfmLogger

logger = QaTrfmLogger.getQatrfmLogger(__name__)


class SimpleTest(TrfmTestCase):

    def __init__(self, env, name):
        description = "Example how to transfer files from/to VMs"
        super(SimpleTest, self).__init__(env, name, description)

    def run(self):
        file_to_transfer = (
            "{}/test_file".format(os.path.dirname(os.path.abspath(__file__))))

        vm1 = self.env.domains[0]

        # Using qemu-agent to execute commands
        vm1.execute_cmd('echo -e "foo\nbar" > /root/some_file')
        vm1.execute_cmd('cat /root/some_file | grep ba')

        # Transfering a file from a VM
        out_file = Path(self.env.workdir) / 'resolv.conf'
        vm1.transfer_file(remote_file_path='/etc/resolv.conf',
                          local_file_path=out_file,
                          type='get')
        logger.success(out_file.read_text())

        # Transfer file to a VM
        vm1.transfer_file(remote_file_path='/root/test_file',
                          local_file_path=file_to_transfer,
                          type='put')

        # Execute SSH command on a VM
        vm1.execute_ssh_cmd('chmod +x /root/test_file; /root/test_file')

        return self.EX_OK
