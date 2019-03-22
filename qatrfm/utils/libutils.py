#!/usr/bin/env python3
#
# Copyright © 2019 SUSE LLC
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.

import os
import signal
import subprocess
from threading import Timer

from qatrfm.utils.logger import QaTrfmLogger
logger = QaTrfmLogger.getQatrfmLogger(__name__)


class TrfmDeployError(Exception):
    pass


class TrfmDomainTimeout(Exception):
    pass


class TrfmDomainNotReachable(Exception):
    pass


class TrfmCommandFailed(Exception):
    pass


class TrfmCommandTimeout(Exception):
    pass


class TrfmSnapshotFailed(Exception):
    pass


class TrfmQemuAgentNotReady(Exception):
    pass


def execute_bash_cmd(cmd, timeout=300, exit_on_failure=True, cwd=os.getcwd()):
    logger.debug("Bash command: '{}'".format(cmd))
    output = ''

    def timer_finished(p):
        logger.error("Bash command timed out")
        timer.cancel()
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        if exit_on_failure:
            raise TrfmCommandTimeout(output)
        return output

    p = subprocess.Popen(cmd, shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, cwd=cwd)
    timer = Timer(timeout, timer_finished, args=[p])
    timer.start()
    for line in iter(p.stdout.readline, b''):
        output += line.decode("utf-8")
        logger.debug(line.rstrip().decode("utf-8"))
    p.stdout.close()
    retcode = p.wait()
    timer.cancel()
    if (retcode != 0 and exit_on_failure):
        raise TrfmCommandFailed(output)
    return output
