#!/usr/bin/env python3
#
# Copyright © 2019 SUSE LLC
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.

""" CLI tool for QATRFM library.

Allows calling this library in a simple way via CLI based on Click with only
one command that creates the environment runs the tests.
"""


import click
import importlib.util
import inspect
import os
import sys

from qatrfm.utils.logger import QaTrfmLogger
from qatrfm.environment import TerraformEnv
from qatrfm.testcase import TrfmTestCase


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo('Version: 0.1\n'
               'Author:  Jose Lausuch <jalausuch@suse.com>')
    ctx.exit()


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--version', '-v', is_flag=True, callback=print_version,
              expose_value=False, is_eager=True)
@click.option('--test', '-t', required=True,
              help='Testcase(s) name(s). Single name or a list separated by '
              'comas of the Class(es) in path to be executed.')
@click.option('--path', '-p', required=True,
              help='Path of the test file.')
@click.option('--hdd', '-d', required=True, help='Path to HDD image.')
@click.option('--num_domains', '-n', default=1,
              help='Number of domains to be created. Default=1')
@click.option('--cores', '-c', default=1, help='Num cores of the domains. '
              'Default=1')
@click.option('--ram', '-r', default=1024, help='Ram of the domains in MB. '
              'Default=1024')
@click.option('--snapshots', '-s', is_flag=True,
              help='Create snapshots of the domains at the beginning. '
              'This is useful to allow the test revert the domains to their '
              'initial state if needed.')
@click.option('--no-clean', 'no_clean', is_flag=True,
              help="Don't clean the environment when the tests finish. "
              "This is useful for debug and troubleshooting.")
def cli(test, path, hdd, num_domains, cores, ram, snapshots, no_clean):
    """ Create a terraform environment and run the test(s)"""

    logger = QaTrfmLogger.getQatrfmLogger(__name__)
    test_array = test.split(',')

    basedir, filename = os.path.split(path)
    tf_file = None
    for file in os.listdir(basedir):
        if file.endswith(".tf"):
            tf_file = os.path.join(basedir, file)
    env = TerraformEnv(image=hdd,
                       tf_file=tf_file,
                       num_domains=num_domains,
                       snapshots=snapshots)

    spec = importlib.util.spec_from_file_location(filename, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    testcases = []
    for t in test_array:
        cls = None
        for member in inspect.getmembers(module):
            if member[0] == t:
                cls = member[1]
        if (cls is None):
            sys.exit("There is no Class named '{}' in {}".format(t, path))
        testcases.append(cls(env, t))

    logger.info("Test case information:\n"
                "\t\tTest case(s): {}\n"
                "\t\tEnvironment:\n"
                "\t\t  Working dir.: {}\n"
                "\t\t  Clean       : {}\n"
                "\t\t  Snapshots   : {}\n"
                "\t\tDomains:\n"
                "\t\t  Count  : {}\n"
                "\t\t  Image  : {}\n"
                "\t\t  Cores  : {}\n"
                "\t\t  RAM    : {}\n"
                "\t\t  Network: {}\n"
                .format(test, env.workdir, not no_clean, snapshots,
                        num_domains, hdd, cores, ram, env.networks[0]))

    failed_tests = []

    try:
        env.deploy()
        for t in testcases:
            logger.info("Running test case '{}' ...".format(t.name))

            exit_code = t.run()
            if (exit_code == TrfmTestCase.EX_OK):
                logger.success("The test '{}' finished successfuly".
                               format(t.name))
            else:
                failed_tests.append(t.name)
                logger.error("The test '{}' finished with error code={}".
                             format(t.name, exit_code))

    except Exception as e:
        logger.error("Something went wrong:\n{}".format(e))
        if (not no_clean):
            env.clean()
        raise(e)

    if (not no_clean):
        env.clean()

    if (len(testcases) > 1):
        if (len(failed_tests) > 0):
            logger.error("The following tests failed: {}".
                         format(failed_tests))
            sys.exit(TrfmTestCase.EX_FAILURE)
        else:
            logger.success("Overall status = GREEN")
            sys.exit(TrfmTestCase.EX_OK)
