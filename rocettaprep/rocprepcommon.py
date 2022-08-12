#!/usr/bin/env python3
#
# rocprepcommon.py
#
# Common utilities.


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

