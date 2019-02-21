#!/usr/bin/env python

import json
import random
import os
import shutil
import string
import sys
import time

from qatrfm.domain import Domain
from qatrfm.utils.logger import Logger
from qatrfm.utils import libutils


class TerraformEnv(object):

    logger = Logger(__name__).getLogger()
    BASEDIR = '/root/terraform/'

    def __init__(self, tf_file=None, num_domains=1, snapshots=False):
        if (tf_file is None):
            path = os.path.dirname(os.path.realpath(__file__))
            self.tf_file = ("{}/config/simple_1net.tf".format(path))
        else:
            self.tf_file = tf_file

        if (not os.path.isfile(self.tf_file)):
            self.logger.error("\033[1;91mFile {} not found.\033[0m".
                              format(self.tf_file))
            sys.exit(-1)
        self.logger.debug("Terraform TF file: {}".format(self.tf_file))
        self.num_domains = num_domains
        self.snapshots = snapshots
        letters = string.ascii_lowercase
        self.workdir = (
            self.BASEDIR + ''.join(random.choice(letters) for i in range(10)))
        os.makedirs(self.workdir)
        self.logger.debug("Using working directory {}".format(self.workdir))
        shutil.copy(self.tf_file, self.workdir + '/env.tf')
        os.chdir(self.workdir)
        self.domains = []
        self.networks = []
        self.networks.append(self.get_network())
        # TODO: check how many networks the user needs and fill this array
        #       accordingly

    @staticmethod
    def get_network():
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
        """ Return an array of Domain objects """
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

        If snapshots == True, after the domains are up, it will create a
        snapshot for each domain in case they are needed to be reverted
        at a certain point of the test flow.
        """

        self.logger.info("\033[1;94mDeploying Terraform Environment\033[0m")

        try:
            [ret, output] = libutils.execute_bash_cmd('terraform init')
        except (libutils.TrfmCommandFailed, libutils.TrfmCommandTimeout) as e:
            self.logger.error("\033[1;91m{}\033[0m".format(e))
            self.clean(remove_terraform_env=False)
            sys.exit(-1)

        try:
            cmd = ("terraform apply -auto-approve "
                   "-var \"network={}\" "
                   "-var \"count={}\"".
                   format(self.networks[0], self.num_domains))
            [ret, output] = libutils.execute_bash_cmd(cmd, timeout=400)
        except (libutils.TrfmCommandFailed, libutils.TrfmCommandTimeout) as e:
            self.logger.error("\033[1;91m{}\033[0m".format(e))
            self.clean()
            sys.exit(-1)

        self.domains = self.get_domains()

        self.logger.debug("\033[1;94mWaiting for domains to be "
                          "ready...\033[0m")
        for domain in self.domains:
            domain.wait_for_qemu_agent_ready()
            if (domain.ip is not None):
                domain.wait_for_ip_ready()
                domain.wait_for_ssh_ready()

        if (self.snapshots):
            self.logger.debug("\033[1;94mCreating snapshots of "
                              "domains...\033[0m")
            for domain in self.domains:
                try:
                    domain.snapshot(action='create')
                except libutils.TrfmSnapshotFailed:
                    sys.exit(-1)
        self.logger.info("\033[1;92mEnvironment deployed successfully\033[0m")

    def reset(self):
        """ Reverts the domains to their initial snapshots """

        self.logger.info("\033[1;94mReseting the Terraform Environment\033[0m")
        if (not self.snapshots):
            # Nothing to reset
            return
        for domain in self.domains:
            try:
                domain.snapshot(action='revert')
                time.sleep(5)
            except libutils.TrfmSnapshotFailed:
                shutil.rmtree(self.workdir)
                sys.exit(-1)

    def clean(self, remove_terraform_env=True):
        self.logger.info("\033[1;94mRemoving Terraform Environment\033[0m")
        if (remove_terraform_env):
            if (self.snapshots):
                for domain in self.domains:
                    try:
                        domain.snapshot(action='delete')
                    except libutils.TrfmSnapshotFailed:
                        shutil.rmtree(self.workdir)
                        sys.exit(-1)
            cmd = ("terraform destroy -auto-approve "
                   "-var \"network={}\" "
                   "-var \"count={}\"".
                   format(self.networks[0], self.num_domains))
            try:
                [ret, output] = libutils.execute_bash_cmd(cmd)
            except (libutils.TrfmCommandFailed,
                    libutils.TrfmCommandTimeout) as e:
                self.logger.error("\033[1;91m{}\033[0m".format(e))
                shutil.rmtree(self.workdir)
                sys.exit(-1)

        shutil.rmtree(self.workdir)
        self.logger.info("\033[1;92mEnvironment clean\033[0m")
