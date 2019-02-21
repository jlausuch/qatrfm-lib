#!/usr/bin/env python

import logging


class QaTrfmLogger(logging.Logger):

    def __init__(self, logger_name, level="DEBUG"):
        format = "\033[1;37;48mqatrfm.%(levelname)s: \033[0m%(message)s"
        logging.basicConfig(level=logging.DEBUG, format=format)
        return super(QaTrfmLogger, self).__init__(logger_name, level)

    def info(self, msg, *args, **kwargs):
        msg = ("\033[1;34m{}\033[0m".format(msg))
        super(QaTrfmLogger, self).info(msg, *args, **kwargs)

    def success(self, msg, *args, **kwargs):
        msg = ("\033[1;32m{}\033[0m".format(msg))
        super(QaTrfmLogger, self).info(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        msg = ("\033[1;31m{}\033[0m".format(msg))
        super(QaTrfmLogger, self).error(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        msg = ("\033[1;33m{}\033[0m".format(msg))
        super(QaTrfmLogger, self).warning(msg, *args, **kwargs)

    @staticmethod
    def getQatrfmLogger(name):
        return logging.getLogger(name)


logging.setLoggerClass(QaTrfmLogger)
logging.getLogger("paramiko.transport").setLevel(logging.WARNING)
logging.getLogger("paramiko.transport.sftp").setLevel(logging.WARNING)
