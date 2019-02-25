#!/usr/bin/env python3
#
# Copyright © 2019 SUSE LLC
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.

""" Terraform environment

Defines how the Terraform deployment looks like and implements the
appropriate calls to deploy and destroy the environment. All the possible
parameters are passed to the corresponding .tf file which terraform will
use to create the libvirt objects (networks, disks, domains)

"""

import json
import random
import os
import shutil
import string
import sys
import time

from qatrfm.domain import Domain
from qatrfm.utils.logger import QaTrfmLogger
from qatrfm.utils import libutils


class TerraformEnv(object):

    logger = QaTrfmLogger.getQatrfmLogger(__name__)
    BASEDIR = '/root/terraform/'

    def __init__(self, image, tf_file=None, num_domains=1,
                 cores=1, ram=1024, snapshots=False):
        """Initialize Terraform Environment object."""
        self.image = image
        if (not os.path.isfile(self.image)):
            self.logger.error("Image file {} not found.".format(self.image))
            sys.exit(-1)

        if (tf_file is None):
            path = os.path.dirname(os.path.realpath(__file__))
            self.tf_file = ("{}/config/simple_1net.tf".format(path))
        else:
            self.tf_file = tf_file

        if (not os.path.isfile(self.tf_file)):
            self.logger.error("File {} not found.".format(self.tf_file))
            sys.exit(-1)
        self.logger.debug("Terraform TF file: {}".format(self.tf_file))
        self.num_domains = num_domains
        self.cores = cores
        self.ram = ram
        self.snapshots = snapshots
        letters = string.ascii_lowercase
        self.basename = ''.join(random.choice(letters) for i in range(10))
        self.workdir = self.BASEDIR + self.basename
        os.makedirs(self.workdir)
        self.logger.debug("Using working directory {}".format(self.workdir))
        shutil.copy(self.tf_file, self.workdir + '/env.tf')
        os.chdir(self.workdir)
        self.domains = []
        self.networks = []
        self.networks.append(self.get_network())
        self.logger.debug("Using network {} for the domains".
                          format(self.networks[0]))
        # TODO: check how many networks the user needs and fill this array
        #       accordingly

    @staticmethod
    def get_network():
        """
        Find a non-used network in the system

        To allow multiple environments co-exist, network ranges can't be
        hardcoded. Otherwise, new libvirt virtual networks can't be created.
        This method offers a network range which is not currently used in the
        range 10.0.0.0/24.
        The second octet is a random number between 1 and 254.
        The third octet is iterated from 1 to 254 until there is a non-used
        range in the sytem.
        """
        [ret, output] = libutils.execute_bash_cmd('ip route')
        x = random.randint(1, 254)
        y = 1
        while y < 255:
            if "10.{}.{}.0".format(x, y) in output:
                y += 1
            else:
                break
        if y == 255:
            raise Exception("Cannot find available network range")
        return "10.{}.{}.0/24".format(x, y)

    @staticmethod
    def get_domains():
        """
        Return an array of Domain objects

        Query terraform to get the names of the domains to create the objects.
        """
        domains = []
        cmd = "terraform output -json domain_names"
        [ret, output] = libutils.execute_bash_cmd(cmd)
        domain_names = json.loads(output)['value']

        cmd = "terraform output -json domain_ips"
        [ret, output] = libutils.execute_bash_cmd(cmd)
        domain_ips = json.loads(output)['value']

        # format of domain_names: ['name1', 'name2']
        # format of domain_ips: [['10.40.1.81'], ['10.40.1.221']]  or [[],[]]
        i = 0
        while i < len(domain_names):
            if (domain_ips[i] == []):
                ip = None
            else:
                ip = domain_ips[i][0]
            domains.append(Domain(domain_names[i], ip))
            i += 1

        return domains

    def deploy(self):
        """ Deploy Environment

        It creates the Terraform environment from the given .tf file

        If snapshots is set to True, after the domains are up, it will create a
        snapshot for each domain in case they are needed to be reverted
        at a certain point of the test flow.
        """

        self.logger.info("Deploying Terraform Environment ...")

        try:
            cmd = 'terraform init'
            if ('LOG_COLORS' not in os.environ):
                cmd = ("{} -no-color".format(cmd))
            [ret, output] = libutils.execute_bash_cmd(cmd)
        except (libutils.TrfmCommandFailed, libutils.TrfmCommandTimeout) as e:
            self.logger.error(e)
            self.clean(remove_terraform_env=False)
            sys.exit(-1)

        try:
            cmd = ("terraform apply -auto-approve "
                   "-var \"basename={}\" "
                   "-var \"image={}\" "
                   "-var \"network={}\" "
                   "-var \"cores={}\" "
                   "-var \"ram={}\" "
                   "-var \"count={}\"".
                   format(self.basename, self.image, self.networks[0],
                          self.cores, self.ram, self.num_domains))
            if ('LOG_COLORS' not in os.environ):
                cmd = ("{} -no-color".format(cmd))
            [ret, output] = libutils.execute_bash_cmd(cmd, timeout=400)
        except (libutils.TrfmCommandFailed, libutils.TrfmCommandTimeout) as e:
            self.logger.error(e)
            self.clean()
            sys.exit(-1)

        self.domains = self.get_domains()

        self.logger.info("Waiting for domains to be ready...")
        for domain in self.domains:
            domain.wait_for_qemu_agent_ready()
            if (domain.ip is not None):
                domain.wait_for_ip_ready()
                domain.wait_for_ssh_ready()

        if (self.snapshots):
            self.logger.debug("Creating snapshots of domains...")
            for domain in self.domains:
                try:
                    domain.snapshot(action='create')
                except libutils.TrfmSnapshotFailed:
                    sys.exit(-1)
        self.logger.success("Environment deployed successfully.")

    def reset(self):
        """ Reverts the domains to their initial snapshots """

        self.logger.info("Reseting the Terraform Environment...")
        if (not self.snapshots):
            # Nothing to reset
            return
        for domain in self.domains:
            try:
                domain.snapshot(action='revert')
                time.sleep(5)
            except libutils.TrfmSnapshotFailed as e:
                shutil.rmtree(self.workdir)
                raise(e)

    def clean(self, remove_terraform_env=True):
        """ Destroys the Terraform environment """
        self.logger.info("Removing Terraform Environment...")
        if (remove_terraform_env):
            if (self.snapshots):
                for domain in self.domains:
                    try:
                        domain.snapshot(action='delete')
                    except libutils.TrfmSnapshotFailed as e:
                        shutil.rmtree(self.workdir)
                        raise(e)
            cmd = ("terraform destroy -auto-approve "
                   "-var \"basename={}\" "
                   "-var \"image={}\" "
                   "-var \"network={}\" "
                   "-var \"cores={}\" "
                   "-var \"ram={}\" "
                   "-var \"count={}\"".
                   format(self.basename, self.image, self.networks[0],
                          self.cores, self.ram, self.num_domains))
            if ('LOG_COLORS' not in os.environ):
                cmd = ("{} -no-color".format(cmd))
            try:
                [ret, output] = libutils.execute_bash_cmd(cmd)
            except (libutils.TrfmCommandFailed,
                    libutils.TrfmCommandTimeout) as e:
                self.logger.error(e)
                shutil.rmtree(self.workdir)
                raise(e)

        shutil.rmtree(self.workdir)
        self.logger.success("Environment clean")
