#!/usr/bin/env python

import os
import signal
import subprocess
from threading import Timer

from qatrfm.utils.logger import Logger
logger = Logger(__name__).getLogger()


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


def execute_bash_cmd(cmd, timeout=300, exit_on_failure=True):
    logger.debug("Bash command: '{}'".format(cmd))
    output = ''

    def timer_finished(p):
        logger.error("\033[91mBash command timed out\033[0m")
        timer.cancel()
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        if exit_on_failure:
            raise TrfmCommandTimeout(output)
        return [-1, output]

    p = subprocess.Popen(cmd, shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    timer = Timer(timeout, timer_finished, args=[p])
    timer.start()
    for line in iter(p.stdout.readline, b''):
        output += line.decode("utf-8")
        print(line.rstrip().decode("utf-8"))
    p.stdout.close()
    retcode = p.wait()
    timer.cancel()
    if (retcode != 0 and exit_on_failure):
        raise TrfmCommandFailed(output)
    return [retcode, output]
