#!/usr/bin/env python

import click
import importlib.util
import inspect
import os
import sys

from qatrfm.utils.logger import QaTrfmLogger
from qatrfm.environment import TerraformEnv
from qatrfm.testcase import TrfmTestCase


@click.command()
@click.option('--test', '-t', required=True,
              help='Test case name, same name as the Class.')
@click.option('--path', '-p', required=True,
              help='Path of the test file.')
@click.option('--hdd', '-h', required=True, help='Path to HDD image.')
@click.option('--num_domains', '-n', default=1,
              help='Number of domains to be created.')
@click.option('--cores', '-c', default=2, help='Num cores of the domains.')
@click.option('--ram', '-r', default=1024, help='Ram of the domains in MB.')
@click.option('--snapshots', '-s', is_flag=True,
              help='Use libvirt snapshots for the domains.')
@click.option('--no-clean', 'no_clean', is_flag=True,
              help='Use libvirt snapshots for the domains.')
@click.option('--tf-file', 'tf_file', default=None,
              help='Use custom .tf file for Terraform instead of default.')
def run(test, path, hdd, num_domains, cores, ram, snapshots,
        no_clean, tf_file):
    logger = QaTrfmLogger.getQatrfmLogger(__name__)
    env = TerraformEnv(image=hdd,
                       tf_file=tf_file,
                       num_domains=num_domains,
                       snapshots=snapshots)

    _, filename = os.path.split(path)
    spec = importlib.util.spec_from_file_location(filename, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    cls = None
    for member in inspect.getmembers(module):
        if member[0] == test:
            cls = member[1]

    testcase = cls(env, test)

    logger.info("Test case information:\n"
                "\t\tTEST      : {}\n"
                "\t\tDESCRPT.  : {}\n"
                "\t\tHDD       : {}\n"
                "\t\tDOMAINS   : {}\n"
                "\t\tCORES     : {}\n"
                "\t\tRAM       : {}\n"
                "\t\tWORKDIR   : {}\n"
                "\t\tNETWORK   : {}\n"
                "\t\tCLEAN     : {}\n"
                "\t\tSNAPSHOTS : {}\n"
                .format(test, testcase.description, hdd, num_domains,
                        cores, ram, env.workdir, env.networks[0],
                        not no_clean, snapshots))
    exit_status = TrfmTestCase.EX_OK

    try:
        env.deploy()
        logger.info("Running test case '{}' ...".format(test))
        if (testcase.run() != TrfmTestCase.EX_OK):
            exit_status = TrfmTestCase.EX_RUN_ERROR

    except Exception as e:
        logger.error("Something went wrong:\n{}".format(e))
        if (not no_clean):
            env.clean()
        raise(e)

    if (not no_clean):
        env.clean()
    logger.info("The test finished with status={}".format(exit_status))
    sys.exit(exit_status)


if __name__ == '__main__':
    run()
