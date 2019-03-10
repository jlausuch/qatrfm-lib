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

from qatrfm.environment import TerraformEnv
from qatrfm.utils import libutils
from qatrfm.utils.logger import QaTrfmLogger
from qatrfm.testcase import TrfmTestCase


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo('Version: 0.1\n'
               'Author:  Jose Lausuch <jalausuch@suse.com>')
    ctx.exit()


def check_image(vars):
    for var in vars:
        v = var.split("=")
        if (v[0] == 'image'):
            if (not os.path.isfile(v[1])):
                raise FileNotFoundError("No such image file {}".format(v[1]))
            return True
    raise libutils.TrfmMissingVariable(
        "TF Parameter 'image' must be provided: "
        "qatrfm ....  --tfvar image=<image_path>")


def find_tf_file(basedir):
    for file in os.listdir(basedir):
        if file.endswith(".tf"):
            return os.path.join(basedir, file)
    return None


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'],
                        max_content_width=200)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--version', '-v', is_flag=True, callback=print_version,
              expose_value=False, is_eager=True)
@click.option('--test', '-t', required=True,
              help='Testcase(s) name(s). Single name or a list separated by '
              'comas of the Class(es) in path to be executed.')
@click.option('--path', '-p', required=True,
              help='Path of the test file.')
@click.option('--tfvar', type=str, multiple=True, help='Variable to '
              'insert to the .tf file. It can be used multiple times '
              'for each single variable. At least tfvar "image" should be '
              'provided for the default .tf file.')
@click.option('--snapshots', is_flag=True,
              help='Create snapshots of the domains at the beginning. '
              'This is useful to allow the test revert the domains to their '
              'initial state if needed.')
@click.option('--no-clean', 'no_clean', is_flag=True,
              help="Don't clean the environment when the tests finish. "
              "This is useful for debug and troubleshooting.")
def cli(test, path, tfvar, snapshots, no_clean):
    """ Create a terraform environment and run the test(s)"""

    logger = QaTrfmLogger.getQatrfmLogger(__name__)
    test_array = test.split(',')

    basedir, filename = os.path.split(path)

    tf_file = find_tf_file(basedir)

    if (tf_file is None):
        path_tf = os.path.dirname(os.path.realpath(__file__))
        tf_file = ("{}/config/default.tf".format(path_tf))
        check_image(tfvar)
    if (not os.path.isfile(tf_file)):
        raise FileNotFoundError("No such file {}".format(tf_file))

    env = TerraformEnv(tf_vars=tfvar, tf_file=tf_file, snapshots=snapshots)

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

    msg = ("Test case information:\n"
           "\t\tTest case(s) : {}\n"
           "\t\tTests path   : {}\n"
           "\t\tWorking dir. : {}\n"
           "\t\tNetwork      : 10.{}.0.0/24\n"
           "\t\tClean        : {}\n"
           "\t\tSnapshots    : {}\n"
           "\t\tTF variables :\n"
           .format(test, path, env.workdir, env.net_octet,
                   not no_clean, snapshots))
    for var in tfvar:
        msg += "\t\t    {}\n".format(var)

    logger.info(msg)

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
            logger.success("All tests passed")
            sys.exit(TrfmTestCase.EX_OK)
