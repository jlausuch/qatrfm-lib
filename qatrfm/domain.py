#!/usr/bin/env python

import time

from qatrfm.utils import logger
from qatrfm.utils import libutils
from qatrfm.utils import qemu_agent_utils as qau


class Domain(object):

    logger = logger.Logger(__name__).getLogger()

    def __init__(self, name, ip):
        self.name = name
        self.ip = ip

    def login(self):
        self.logger.info("Login")

    def execute_cmd(self, cmd, timeout=300, exit_on_failure=True):
        self.logger.info("execute_cmd '{}'".format(cmd))
        str = qau.generate_guest_exec_str(self.name, cmd)
        out_json = libutils.execute_bash_cmd(str)[1]
        pid = qau.get_pid(out_json)
        self.logger.debug("The command has PID={}".format(pid))
        i = 0
        str = qau.generate_guest_exec_status(self.name, pid)
        while i < timeout:
            out_json = libutils.execute_bash_cmd(str)[1]
            if qau.process_is_exited(out_json):
                retcode = qau.get_ret_code(out_json)
                output = qau.get_output(out_json)
                if (retcode != 0):
                    err_data = qau.get_output(out_json, 'err-data')
                    self.logger.error("The command failed with exit code {}. "
                                      "Reason:\n  {}"
                                      .format(retcode, err_data))
                    if (exit_on_failure):
                        raise libutils.TrfmCommandFailed()
                else:
                    self.logger.debug("The command '{}' on the domain '{}' "
                                      "succedded.\nOUTPUT:\n{}"
                                      .format(cmd, self.name, output))
                if (retcode != 0 and exit_on_failure):
                    raise libutils.TrfmCommandFailed()
                return [retcode, output]
            time.sleep(1)
            i += 1
        self.logger.error("The command '{}' on the domain '{}' timed out."
                          .format(cmd, self.name))
        if (exit_on_failure):
            raise libutils.TrfmCommandTimeout()

    def copy_file(self, source_path, target_path):
        self.logger.info("copy local file from {} to {}"
                         .format(source_path, target_path))
