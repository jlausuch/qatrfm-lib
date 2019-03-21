#!/usr/bin/env python3
#
# Copyright © 2019 SUSE LLC
#
# Copying and distribution of this file, with or without modification,
# are permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.  This file is offered as-is,
# without any warranty.

import base64
import json


def generate_guest_exec_str(domain, cmd):
    return ('virsh -c qemu:///system qemu-agent-command --domain {} --cmd '
            '\'{{ \"execute\": \"guest-exec\", \"arguments\": {{ \"path\": '
            '\"bash\", \"arg\": [\"-c\", \"{}\"], \"capture-output\": true'
            '}}}}\''.format(domain, cmd))


def generate_guest_exec_status(domain, pid):
    return ('virsh -c qemu:///system qemu-agent-command --domain {} --cmd '
            '\'{{ \"execute\": \"guest-exec-status\", \"arguments\":'
            ' {{ \"pid\": {} }}}}\''.format(domain, pid))


def generate_guest_ping_str(domain):
    return ('virsh -c qemu:///system qemu-agent-command --domain {} --cmd '
            '\'{{ \"execute\": \"guest-ping\"}}\''.format(domain))


def get_pid(str):
    return json.loads(str)["return"]["pid"]


def get_ret_code(str):
    return json.loads(str)["return"]["exitcode"]


def process_is_exited(str):
    if (json.loads(str)["return"]["exited"]):
        return True
    return False


def get_output(str, field='out-data'):
    output = ''
    try:
        output = (
            base64.b64decode(json.loads(str)["return"][field]).decode("utf-8"))
    except Exception:
        pass
    return output
