#!/usr/bin/env python
import shlex
import subprocess
from threading import Timer

from qatrfm.utils.logger import Logger
logger = Logger(__name__).getLogger()


class TrfmDeployError(Exception):
    pass

class TrfmCommandFailed(Exception):
    pass

class TrfmCommandTimeout(Exception):
    pass


def execute_bash_cmd(cmd, timeout = 300, exit_on_failure = True):
    logger.debug("Bash command: '{}'".format(cmd))
    p = subprocess.Popen(shlex.split(cmd), shell=False,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        output = p.communicate(timeout=timeout)[0].decode("utf-8")
        retcode = p.wait()
        if (retcode != 0 and exit_on_failure):
            raise TrfmCommandFailed("Bash command '{}' failed. Reason:\n"
                "{}".format(cmd, output))
        else:
            logger.debug("Bash command result:\n RET CODE: {}\n OUTPUT:\n{}".format(retcode, output))
            return [retcode, output]
    except subprocess.TimeoutExpired:
        p.kill()
        if (exit_on_failure):
            raise TrfmCommandTimeout("The bash command '{}' timed out.".format(cmd))


    
    
