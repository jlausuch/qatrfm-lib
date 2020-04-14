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
import os
import shutil
import string
import sys
import random
import tempfile
import time

from pathlib import Path

from qatrfm.domain import Domain
from qatrfm.utils.logger import QaTrfmLogger
from qatrfm.utils import libutils


class TerraformCmd:

    logger = QaTrfmLogger.getQatrfmLogger(__name__)

    def __init__(self, tf_file, tf_vars=None):
        self.tf_file = tf_file
        self.logger.info("Terraform TF file: {}".format(self.tf_file))
        if tf_vars:
            self.tf_vars = TerraformCmd.vars_to_string(tf_vars)
        self.workdir = tempfile.mkdtemp()
        self.logger.debug("Using working directory {}".format(self.workdir))
        shutil.copy(self.tf_file, self.workdir + '/env.tf')

    @staticmethod
    def vars_to_string(vars):
        s = ''
        for v in vars:
            kv = v.split('=', 1)
            if (Path(kv[1]).is_file()):
                kv[1] = Path(kv[1]).resolve()
            s += "-var '{}={}' ".format(kv[0], kv[1])
        return s

    def deploy(self):
        """ Deploy Environment

        It creates the Terraform environment from the given .tf file

        """

        self.logger.info("Deploying Terraform Environment ...")

        try:
            cmd = 'terraform init'
            if ('LOG_COLORS' not in os.environ):
                cmd = ("{} -no-color".format(cmd))
            libutils.execute_bash_cmd(cmd, cwd=self.workdir)
        except (libutils.TrfmCommandFailed, libutils.TrfmCommandTimeout) as e:
            self.logger.error(e)
            sys.exit(-1)

        try:
            cmd = "terraform apply -input=false -auto-approve {}".format(
                self.tf_vars)
            if ('LOG_COLORS' not in os.environ):
                cmd = ("{} -no-color".format(cmd))
            libutils.execute_bash_cmd(cmd, timeout=400, cwd=self.workdir)
        except (libutils.TrfmCommandFailed, libutils.TrfmCommandTimeout) as e:
            self.logger.error(e)
            self.clean()
            sys.exit(-1)

    def clean(self):
        """ Destroys the Terraform environment """
        self.logger.info("Removing Terraform Environment...")
        cmd = "terraform destroy -input=false -auto-approve {}".format(
            self.tf_vars)
        if ('LOG_COLORS' not in os.environ):
            cmd = ("{} -no-color".format(cmd))
        try:
            libutils.execute_bash_cmd(cmd, cwd=self.workdir)
        except (libutils.TrfmCommandFailed,
                libutils.TrfmCommandTimeout) as e:
            self.logger.error(e)
            shutil.rmtree(self.workdir)
            raise(e)

        shutil.rmtree(self.workdir)
        self.logger.success("Environment clean")


class TerraformEnv(TerraformCmd):

    def __init__(self, net_octet, tf_vars, tf_file, snapshots=False):
        """Initialize Terraform Environment object."""
        self.snapshots = snapshots
        letters = string.ascii_lowercase
        self.basename = ''.join(random.choice(letters) for i in range(10))
        self.domains = []
        self.net_octet = net_octet
        tf_vars.add('basename=' + self.basename)
        tf_vars.add('net_octet={}'.format(self.net_octet))
        super().__init__(tf_file, tf_vars)

    def get_domains(self):
        """
        Return an array of Domain objects

        Query terraform to get the names of the domains to create the objects.
        """
        domains = []
        cmd = "terraform output -json domain_names"
        output = libutils.execute_bash_cmd(cmd, cwd=self.workdir)
        domain_names = json.loads(output)['value']

        cmd = "terraform output -json domain_ips"
        output = libutils.execute_bash_cmd(cmd, cwd=self.workdir)
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

        super().deploy()

        self.domains = self.get_domains()

        self.logger.info("Waiting for domains to be ready...")
        for domain in self.domains:
            if (domain.ip):
                domain.wait_for_ip_ready()
                domain.wait_for_ssh_ready()
            else:
                domain.wait_for_qemu_agent_ready()

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

    def clean(self):
        """ Destroys the Terraform environment """
        if (self.snapshots):
            for domain in self.domains:
                try:
                    domain.snapshot(action='delete')
                except libutils.TrfmSnapshotFailed as e:
                    shutil.rmtree(self.workdir)
                    raise(e)
        super().clean()
