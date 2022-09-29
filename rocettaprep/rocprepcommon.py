#!/usr/bin/env python3
#
# rocprepcommon.py
#
# Common utilities.

import datetime


def load_instruction_list(fname):
    with open(fname, "r") as f:
        x = [l.strip() for l in f.readlines()]

        return list([xx for xx in x if xx and xx[0] != '#'])

def get_instructions(arg):
    if arg is None:
        return []

    if arg[0] == '@':
        return load_instruction_list(arg[1:])
    else:
        return [arg]

class PrepTimer:
    def __init__(self):
        self.start = None
        self.end = None

    def start_timer(self):
        self.start = datetime.datetime.now()
        print("Started at", self.start)

    def end_timer(self):
        self.end = datetime.datetime.now()
        print("End at", self.end)
        print("Total time", self.end - self.start) # should really be monotonic.

