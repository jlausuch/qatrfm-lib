#!/usr/bin/env python

import paramiko
import time

from qatrfm.utils.logger import QaTrfmLogger
from qatrfm.utils import libutils
from qatrfm.utils import qemu_agent_utils as qau


class Domain(object):

    logger = QaTrfmLogger.getQatrfmLogger(__name__)

    def __init__(self, name, ip=None, user='root', pwd='nots3cr3t'):
        self.name = name
        self.ip = ip
        self.user = user
        self.pwd = pwd

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
        self.logger.debug("execute_cmd '{}'".format(cmd))
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
        self.logger.error("The command '{}' on the domain '{}' timed out.".
                          format(cmd, self.name))
        if (exit_on_failure):
            raise libutils.TrfmCommandTimeout

    def wait_for_qemu_agent_ready(self, timeout=300):
        i = 0
        while (i < int(timeout / 10)):
            try:
                self.execute_cmd("hostname")
                self.logger.debug("Qemu agent ready on '{}'".format(self.name))
                return
            except libutils.TrfmCommandFailed:
                i += 1
                time.sleep(10)
        raise libutils.TrfmDomainTimeout

    def wait_for_ip_ready(self, timeout=300):
        i = 0
        while (i < int(timeout / 10)):
            try:
                cmd = "ping -c 1 {}".format(self.ip)
                [ret, output] = libutils.execute_bash_cmd(cmd)
                self.logger.debug("IP '{}' reachable".format(self.ip))
                return
            except libutils.TrfmCommandFailed:
                i += 1
                time.sleep(10)
        raise libutils.TrfmDomainTimeout

    def wait_for_ssh_ready(self, timeout=300):
        i = 0
        while (i < int(timeout / 10)):
            try:
                cmd = "nc -vz -w 1 {} 22".format(self.ip)
                [ret, output] = libutils.execute_bash_cmd(cmd)
                self.logger.debug("SSH on port 22 reachable")
                return
            except libutils.TrfmCommandFailed:
                i += 1
                time.sleep(10)
        self.logger.warning("SSH is not available on the domain.")

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
            self.logger.error("Failed to {} snapshot of domain {}."
                              .format(action, self.name))
            raise libutils.TrfmSnapshotFailed(e)

    def transfer_file(self, remote_file_path, local_file_path, type='get'):
        if (self.ip is None):
            raise libutils.TrfmDomainNotReachable(
                "The domain doesn't have an IP defined")
        self.logger.debug("Transfer file:\n"
                          " domain: {}\n"
                          " ip:     {}\n"
                          " type:   {}\n"
                          " remote_file_path: {}\n"
                          " local_file_path:  {}"
                          .format(self.name, self.ip, type,
                                  remote_file_path, local_file_path))
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
            ssh.connect(hostname=self.ip,
                        username=self.user,
                        password=self.pwd)
            sftp_client = ssh.open_sftp()
            if (type == 'get'):
                sftp_client.get(remote_file_path, local_file_path)
            elif (type == 'put'):
                sftp_client.put(local_file_path, remote_file_path)
            sftp_client.close()
            ssh.close()
            self.logger.debug("File Transfer succedded.")
        except paramiko.ssh_exception.NoValidConnectionsError as e:
            ssh.close()
            self.logger.error("Can't reach IP {} on port 22.\n{}".
                              format(self.ip, e))
            raise(e)
        except paramiko.ssh_exception.AuthenticationException as e:
            ssh.close()
            self.logger.error("Wrong user/password for the Domain {}.".
                              format(self.name))
            raise(e)
        except FileNotFoundError as e:
            self.logger.error(e)
            sftp_client.close()
            raise(e)
