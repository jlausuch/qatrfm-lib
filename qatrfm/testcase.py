#!/usr/bin/env python3
#
# Copyright © 2019 SUSE LLC
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.


""" Testcase Class

A new test case must be inherited from this class and implement
the desired test logic.
"""

import os

from qatrfm.utils.logger import QaTrfmLogger


class TrfmTestCase(object):
    EX_OK = os.EX_OK
    """execution successful"""

    EX_FAILURE = os.EX_SOFTWARE
    """execution failed in some step"""

    def __init__(self, env, name, description=None):
        """Initialize Testcase object."""
        self.env = env
        self.name = name
        self.description = description
        self.logger = QaTrfmLogger.getQatrfmLogger(self.name)

    def run(self):
        """
        Execution of the test case.

        This method must be overriden by the children and implement the
        flow of the test. If everything is ok, self.EX_OK should be returned.
        Otherwise, self.EX_FAILURE should be returned.
        """
        return self.EX_OK
