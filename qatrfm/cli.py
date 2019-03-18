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
import fcntl
import importlib.util
import inspect
import sys
from pathlib import Path

from qatrfm.environment import TerraformEnv
from qatrfm.utils.logger import QaTrfmLogger, init_logging
from qatrfm.utils import libutils
from qatrfm.testcase import TrfmTestCase

file_lock = None


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo('Version: 0.1\n'
               'Author:  Jose Lausuch <jalausuch@suse.com>')
    ctx.exit()


def find_corresponding_tf_file(f: Path):
    assert(f.is_file())
    default_tf = Path(__file__).resolve().parent / 'config' / 'default.tf'
    tf_files = sorted(f.parent.glob('*.tf'))
    if len(tf_files) > 1:
        QaTrfmLogger.getQatrfmLogger(__name__).warning(
                'Found more then one *.tf file for {}'.format(str(f)))
    if len(tf_files):
        return tf_files[0]
    return default_tf


def find_py_files(directory: Path):
    assert(directory.is_dir())
    file_list = []
    for x in directory.iterdir():
        if x.is_file() and x.suffix == '.py':
            file_list.append(x.resolve())
        elif x.is_dir():
            file_list.extend(find_py_files(x))
    return file_list


def load_testcases(basedir: Path, files):
    assert(basedir.is_dir())
    testcases = {}
    for i in files:
        name = str(i.relative_to(basedir))[:-3].replace('/', '.')
        tf_file = find_corresponding_tf_file(i)
        if tf_file not in testcases.keys():
            testcases[tf_file] = []
        spec = importlib.util.spec_from_file_location(str(name), i)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules[str(name)] = mod

        for member in inspect.getmembers(mod, predicate=inspect.isclass):
            if (member[1].__module__ == str(name) and
                    issubclass(member[1], TrfmTestCase)):
                testcases[tf_file].append(member[1])
    return testcases


def find_testcases(opt_test: Path):
    opt_test = opt_test.resolve()
    basedir = opt_test.parent
    if opt_test.is_dir():
        basedir = opt_test
        files = find_py_files(opt_test)
    else:
        files = [opt_test]
    return load_testcases(basedir, files)


def get_network_octet():
    """
    Find a non-used network in the system

    To allow multiple environments co-exist, network ranges can't be
    hardcoded. Otherwise, new libvirt virtual networks can't be created.
    The default environment will create a network with range 10.X.0.0/24,
    where X will be calculated dynamically according to the existing
    networks on the system, starting from X=0, this offers 255 possible
    isolated environments running at the same time.
    """
    global file_lock
    locks_dir = '/tmp/qatrfm'
    Path(locks_dir).mkdir(exist_ok=True)
    x = 0
    while x < 255:
        try:
            file_lock = open('{}/{}'.format(locks_dir, x), 'a')
            [ret, output] = libutils.execute_bash_cmd(
                'ip a|grep 10.{}||true'.format(x))
            if output == '':
                fcntl.flock(file_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return x
        except IOError:
            pass
        x += 1
    raise Exception("Cannot find available network range")


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'],
                        max_content_width=200)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--version', '-v', is_flag=True, callback=print_version,
              expose_value=False, is_eager=True)
@click.option('--test', '-t', required=True,
              help='Testcase(s) name(s). Single name or a list separated by '
              'comas of the Class(es) in path to be executed.')
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
@click.option('--loglevel', 'loglevel', type=click.Choice([
              'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']),
              default='DEBUG', help="Specify default log level")
@click.option('--log-colors', 'logcolors', is_flag=True, help="Show different "
              "loglevels in different colors", envvar='LOG_COLORS')
def cli(test, tfvar, snapshots, no_clean, loglevel, logcolors):
    """ Create a terraform environment and run the test(s)"""

    init_logging(loglevel, logcolors)
    logger = QaTrfmLogger.getQatrfmLogger(__name__)

    testcases = find_testcases(Path(test))
    for tf_file in testcases.keys():
        net_octet = get_network_octet()
        env = TerraformEnv(net_octet=net_octet,
                           tf_vars=tfvar,
                           tf_file=tf_file,
                           snapshots=snapshots)
        logger.info(("Test case information:\n"
                     "\tTF_file      : {}\n"
                     "\tTests        : {}\n"
                     "\tWorking dir. : {}\n"
                     "\tNetwork      : 10.{}.0.0/24\n"
                     "\tClean        : {}\n"
                     "\tSnapshots    : {}\n"
                     "\tTF variables : \n"
                     "{}").format(
                          str(tf_file),
                          ",".join([t.__name__ for t in testcases[tf_file]]),
                          env.workdir, net_octet, not no_clean, snapshots,
                          "\n".join(["\t\t{}".format(v) for v in tfvar])
                   ))

        try:
            failed_tests = []
            env.deploy()
            for test in testcases[tf_file]:
                logger.info("Running test case '{}'".format(test.__name__))
                logger.info("\tfrom module '{}' ".
                            format(sys.modules[test.__module__].__file__))

                t = test(env, test.__name__)
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

        if (len(testcases[tf_file]) > 1 and len(failed_tests) > 0):
            logger.error("The following tests failed: {}".
                         format(",".join(failed_tests)))
            sys.exit(TrfmTestCase.EX_FAILURE)

    logger.success("All tests passed")
    sys.exit(TrfmTestCase.EX_OK)
