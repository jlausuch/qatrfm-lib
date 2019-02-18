#!/usr/bin/env python

import json
import random
import os
import shutil
import string
import sys

from qatrfm.domain import Domain
from qatrfm.utils.logger import Logger
from qatrfm.utils import libutils


class TerraformEnv(object):

    logger = Logger(__name__).getLogger()
    BASEDIR = '/home/jlausuch/terraform/'

    def __init__(self, tf_file):
        self.tf_file = tf_file
        letters = string.ascii_lowercase
        self.workdir = (
            self.BASEDIR + ''.join(random.choice(letters) for i in range(10)))
        os.mkdir(self.workdir)
        self.logger.debug("Using working directory {}".format(self.workdir))
        shutil.copy(self.tf_file, self.workdir + '/env.tf')
        os.chdir(self.workdir)
        self.domains = []
        self.deployed = False

    def deploy(self, snapshots=False):
        """ Deploy Environment

        It creates the Terraform environment from the given .tf file

        If snapshots == True, after the domains are up, it will create a
        snapshot for each domain in case they are needed to be reverted
        at a certain point of the test flow.
        """

        self.logger.info("Deploying Terraform Environment")
        [ret, output] = libutils.execute_bash_cmd('terraform init')
        if ret != 0:
            self.logger.error("There has been a problem"
                              " initializing terraform")
            self.clean()
            sys.exit(1)
        [ret, output] = (
            libutils.execute_bash_cmd('terraform apply -auto-approve'))
        if ret != 0:
            self.clean()
        else:
            self.deployed = True
        self.domains = self.get_domains()

    @staticmethod
    def get_domains():
        """ Return an array of Domain objects """
        domains = []
        cmd = "terraform output -json vm_names"
        [ret, output] = libutils.execute_bash_cmd(cmd)
        domain_names = json.loads(output)['value']
        print('VMS={}'.format(domain_names))
        print('LEN VMS={}'.format(len(domain_names)))

        cmd = "terraform output -json vm_ips"
        [ret, output] = libutils.execute_bash_cmd(cmd)
        domain_ips = json.loads(output)['value']
        print('IPS={}'.format(domain_ips))
        # decode json stuff here
        i = 0
        while i < len(domain_names):
            domains.append(Domain(domain_names[i], domain_ips[i][0]))
            print("NAME = {}".format(domain_names[i]))
            print("IP = {}".format(domain_ips[i]))
            i += 1

        return domains

    def reset(self):
        """ Reverts the domains to their initial snapshots """
        self.logger.info("Reseting the Terraform Environment")

    def clean(self):
        self.logger.info("Remove Environment")
        if (self.deployed):
            [ret, output] = (
                libutils.execute_bash_cmd('terraform destroy -auto-approve'))
            if ret != 0:
                self.logger.error("Cannot clean environment")
            else:
                self.logger.debug("Terraform destroyed")

        shutil.rmtree(self.workdir)
        self.logger.info("Environment cleaned")
