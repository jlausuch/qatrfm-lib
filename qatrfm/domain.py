#!/usr/bin/env python3
#
# Copyright © 2019 SUSE LLC
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.


""" Libvirt domain

It represents a Virtual Machine (Domain) object along with a bunch of
utilities to interact with it.

"""

import paramiko
import time

from qatrfm.utils.logger import QaTrfmLogger
from qatrfm.utils import libutils
from qatrfm.utils import qemu_agent_utils as qau


class Domain(object):

    logger = QaTrfmLogger.getQatrfmLogger(__name__)

    def __init__(self, name, ip=None, user='root', pwd='nots3cr3t'):
        """Initialize Domain object."""
        self.name = name
        self.ip = ip
        self.user = user
        self.pwd = pwd
        # TODO: don't hardcode user/pwd. Allow new input parameters from user.
        # Future: inject ssh keys into VMs from host.
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())

    def _print_log(self, cmd, retcode=None, output=None, type='Qemu agent'):
        self.logger.debug("{} command status:\n"
                          "\t\tDOMAIN  : {}\n"
                          "\t\tCMD     : {}\n"
                          "\t\tRETCODE : {}\n"
                          "\t\tOUTPUT  :\n{}\n"
                          .format(type, self.name, cmd, retcode, output))

    def execute_cmd(self, cmd, timeout=300, exit_on_failure=True):
        """
        Execute a command.

        Executes a command through qemu-agent-command, which is a daemon
        program running inside the domain. It uses 'guest-exec' to run a
        command, querys the result 'guest-exec-status' until the command ends
        and returns a exit code and potential stdout or stderr.
        If the command doesn't finish before a certain 'timeout', the method
        with raise an exception if 'exit_on_failure' is set to True.

        For more info about qemu agent, refer to:
            https://wiki.libvirt.org/page/Qemu_guest_agent
        """
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

    def execute_ssh_cmd(self, cmd, timeout=300, exit_on_failure=True):
        """
        Execute SSH command.

        Executes a command through SSH using paramiko library.
        IP must be not None and reachable.
        If the command doesn't finish before a certain 'timeout', the method
        with raise an exception if 'exit_on_failure' is set to True.

        """
        self.logger.debug("execute ssh cmd '{}'".format(cmd))
        try:
            self.ssh.connect(hostname=self.ip,
                             username=self.user,
                             password=self.pwd)
            (_, stdout, stderr) = self.ssh.exec_command(cmd)
            i = 0
            while not stdout.channel.eof_received:
                print(i)
                time.sleep(1)
                if i > timeout:
                    self.ssh.close()
                    self.logger.error("The command {} timed out after "
                                      "{} seconds.".format(cmd, timeout))
                    if (exit_on_failure):
                        raise libutils.TrfmCommandTimeout
                    return [-1, stdout.read().decode("utf-8")]
                i += 1

            retcode = stdout.channel.recv_exit_status()
            self.ssh.close()
            if (retcode != 0):
                error = stderr.read().decode("utf-8")
                self._print_log(cmd, retcode, error, type='SSH')
                if (exit_on_failure):
                    raise libutils.TrfmCommandFailed(error)
                return [retcode, error]
            else:
                output = stdout.read().decode("utf-8")
                self._print_log(cmd, retcode, output, type='SSH')
            return [retcode, output]
        except paramiko.ssh_exception.NoValidConnectionsError as e:
            self.ssh.close()
            self.logger.error("Can't reach IP {} on port 22.\n{}".
                              format(self.ip, e))
            raise(e)
        except paramiko.ssh_exception.AuthenticationException as e:
            self.ssh.close()
            self.logger.error("Wrong user/password for the Domain {}.".
                              format(self.name))
            raise(e)
        except paramiko.ssh_exception.SSHException as e:
            self.ssh.close()
            self.logger.error("The domain failed to execute the command.")
            raise(e)

    def wait_for_qemu_agent_ready(self, timeout=300):
        """
        Waits for qemu agent available in the domain by running a simple
        command and check that it doesn't fail.
        """
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
        """
        Waits until domain's ip is pingable.

        The user is responsible to use an image which allows ingress ICMP
        traffic.
        """
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
        """
        Waits for domain's TCP port 22 (SSH) is reachable.

        The user is responsible to use an image which allows ingress traffic in
        port 22 TCP. Any firewall rules must be disabled beforehand.
        """
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
        """
        Create a snapshot of the domain

        If desired, snapshots of a domain can be created when the environment
        is freshly deployed. Thus, tests can reset the environment at any point
        to revert the state of a domain as it was right after boot.
        """
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
        """
        Transfer a file from/to the domain via SSH (SCP).

        'type' attribute can be set to 'get' to transfer_file a file from the
        domain to a local path or 'put' to do the opposite.

        """
        if (self.ip is None):
            raise libutils.TrfmDomainNotReachable(
                "The domain doesn't have an IP defined")
        self.logger.debug("Transfer file:\n"
                          "\t\tdomain: {}\n"
                          "\t\tip:     {}\n"
                          "\t\ttype:   {}\n"
                          "\t\tremote_file_path: {}\n"
                          "\t\tlocal_file_path:  {}"
                          .format(self.name, self.ip, type,
                                  remote_file_path, local_file_path))
        try:
            self.ssh.connect(hostname=self.ip,
                             username=self.user,
                             password=self.pwd)
            sftp_client = self.ssh.open_sftp()
            if (type == 'get'):
                sftp_client.get(remote_file_path, local_file_path)
            elif (type == 'put'):
                sftp_client.put(local_file_path, remote_file_path)
            sftp_client.close()
            self.ssh.close()
            self.logger.debug("File Transfer succedded.")
        except paramiko.ssh_exception.NoValidConnectionsError as e:
            self.ssh.close()
            self.logger.error("Can't reach IP {} on port 22.\n{}".
                              format(self.ip, e))
            raise(e)
        except paramiko.ssh_exception.AuthenticationException as e:
            self.ssh.close()
            self.logger.error("Wrong user/password for the Domain {}.".
                              format(self.name))
            raise(e)
        except FileNotFoundError as e:
            self.logger.error(e)
            sftp_client.close()
            raise(e)
