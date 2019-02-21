#!/usr/bin/env python

import os

from qatrfm.utils.logger import QaTrfmLogger


class TrfmTestCase(object):
    EX_OK = os.EX_OK
    """execution successful"""

    EX_RUN_ERROR = os.EX_SOFTWARE
    """execution failed in some step"""

    def __init__(self, env, name, description):
        self.env = env
        self.name = name
        self.description = description
        self.logger = QaTrfmLogger.getQatrfmLogger(self.name)

    def run(self):
        # to ve overriden by the children
        return self.EX_OK
