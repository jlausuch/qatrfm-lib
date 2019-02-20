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

    def _print_log(self, cmd, retcode=None, output=None):
        self.logger.debug("Qemu agent command status:\n"
                          "DOMAIN  : {}\n"
                          "CMD     : {}\n"
                          "RETCODE : {}\n"
                          "OUTPUT  :\n{}\n"
                          .format(self.name, cmd, retcode, output))

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
                    self._print_log(cmd, retcode, err_data)
                    if (exit_on_failure):
                        raise libutils.TrfmCommandFailed
                else:
                    self._print_log(cmd, retcode, output)
                if (retcode != 0 and exit_on_failure):
                    raise libutils.TrfmCommandFailed
                return [retcode, output]
            time.sleep(1)
            i += 1
        self.logger.error("The command '{}' on the domain '{}' timed out."
                          .format(cmd, self.name))
        if (exit_on_failure):
            raise libutils.TrfmCommandTimeout

    def snapshot(self, action):
        if (action == 'create'):
            cmd = ("virsh snapshot-create-as {} --name {}-snapshot"
                   .format(self.name, self.name))
        elif (action == 'delete'):
            cmd = ("virsh snapshot-delete {} --current".
                   format(self.name, self.name))
        elif (action == 'revert'):
            cmd = ("virsh snapshot-revert {} --current".
                   format(self.name, self.name))
        try:
            [ret, output] = libutils.execute_bash_cmd(cmd)
        except libutils.TrfmCommandFailed as e:
            self.logger.error("Failed to {} snapshot of domain {}.".
                              format(action, self.name))
            raise libutils.TrfmSnapshotFailed(e)

    def copy_file(self, source_path, target_path):
        self.logger.info("copy local file from {} to {}"
                         .format(source_path, target_path))
