#!/usr/bin/env python3
#
# roctest.py
#
# Framework to run tests in working directory

import argparse
from pathlib import Path
import json
from build_single_insn import Insn
import tempfile
import os
from collections import namedtuple
from rocprepcommon import *

TestInfo = namedtuple('TestInfo', 'cmdline tmp_output gold_output')

class TempFile:
    def __init__(self, prefix = None, suffix = None, dir_ = None, text = False, path = None):
        self.path = path
        self.prefix = prefix
        self.suffix = suffix
        self.dir_ = dir_
        self.text = text

    def get_name(self):
        if self.path:
            return self.path
        else:
            if hasattr(self, "_tmp_output"):
                return self._tmp_output
            else:
                h, tmp_output = tempfile.mkstemp(prefix=self.prefix)
                os.close(h)
                self._tmp_output = tmp_output
                return tmp_output

    def cleanup(self):
        if not self.path and self._tmp_output:
            os.unlink(self._tmp_output)

    def __str__(self):
        if self.path:
            return f"TempFile(path={repr(self.path)})"
        else:
            return f"TempFile(prefix={repr(self.prefix)},...)"

    __repr__ = __str__

class InsnTest:
    def __init__(self, wp, insn):
        self.wp = wp
        self.insn = insn

    def load_tests(self):
        with open(self.wp.workdir / self.insn.working_dir / "testcases.json", "r") as f:
            self.insn_info = json.load(fp=f)

    def gen_tests(self, binary = None, output = None, filter_fn = lambda x: True):
        if binary is None:
            # run the oracle
            binary = self.wp.workdir / self.insn.working_dir / self.insn.insn

        if output is None:
            tmp_output = TempFile(prefix="output_" + self.insn.insn + "_")
        else:
            tmp_output = TempFile(path = output)

        # TODO: this command-line format doesn't work for all tests
        for t in filter(filter_fn, self.insn_info['tests']):
            yield TestInfo(cmdline=[binary, self.wp.tests_dir / t['input'], tmp_output],
                           tmp_output = tmp_output,
                           gold_output= self.wp.tests_dir / t['output'])

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Run tests (this is a test driver)")
    p.add_argument("workdir", help="Work directory")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")

    args = p.parse_args()
    insns = get_instructions(args.insn)

    if len(insns):
        wp = WorkParams.load_from(args.workdir)

        for i in insns:
            insn = Insn(i)
            it = InsnTest(wp, insn)
            it.load_tests()
            for t in it.gen_tests():
                print(t)
