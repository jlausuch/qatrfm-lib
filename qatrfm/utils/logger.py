#!/usr/bin/env python3
#
# Copyright © 2019 SUSE LLC
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.


""" QaTrfm custom Logger Class

It defines a specific format of the log messages.
"""

import logging


class QaTrfmLogger(logging.Logger):

    colors = False

    def __init__(self, logger_name):
        """Initialize QaTrfmLogger Class"""
        return super().__init__(logger_name)

    @staticmethod
    def colorize(msg, color):
        COLORS_MAP = {
            'blue': 34, 'green': 32, 'red': 31, 'yellow': 33,
            'lightgrey': 37
        }
        if color in COLORS_MAP.keys():
            return "\033[1;{}m{}\033[0m".format(COLORS_MAP[color], msg)
        return msg

    def info(self, msg, *args, **kwargs):
        if (QaTrfmLogger.colors):
            msg = QaTrfmLogger.colorize(msg, 'blue')
        super().info(msg, *args, **kwargs)

    def success(self, msg, *args, **kwargs):
        if (QaTrfmLogger.colors):
            msg = QaTrfmLogger.colorize(msg, 'green')
        super().info(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        if (QaTrfmLogger.colors):
            msg = QaTrfmLogger.colorize(msg, 'red')
        super().error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        if (QaTrfmLogger.colors):
            msg = QaTrfmLogger.colorize(msg, 'red')
        super().critical(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        if (QaTrfmLogger.colors):
            msg = QaTrfmLogger.colorize(msg, 'yellow')
        super().warning(msg, *args, **kwargs)

    @staticmethod
    def getQatrfmLogger(name):
        logging.setLoggerClass(QaTrfmLogger)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger = logging.getLogger(name)
        logger.addHandler(handler)
        return logger


def init_logging(level, colors):
    fmt = "%(levelname)-8s %(name)-12s: %(message)s"
    if colors:
        fmt = QaTrfmLogger.colorize(fmt[:-11], 'lightgrey')
        fmt += '%(message)s'
    logging.basicConfig(level=level, format=fmt)
    logging.getLogger("paramiko.transport").setLevel(logging.WARNING)
    logging.getLogger("paramiko.transport.sftp").setLevel(logging.WARNING)
    QaTrfmLogger.colors = colors
