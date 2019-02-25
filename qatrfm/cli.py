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
              help='Testcase(s) name(s). Single name or a list separated by '
              'comas of the Class(es) in path to be executed.')
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
def run(test, path, hdd, num_domains, cores, ram, snapshots, no_clean):
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
                             format(exit_code))

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
            sys.exit(TrfmTestCase.EX_RUN_ERROR)
        else:
            logger.success("Overall status = GREEN")
            sys.exit(TrfmTestCase.EX_OK)


if __name__ == '__main__':
    run()
