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

    def set_insn_info(self, insn_info):
        self.insn_info = insn_info

    def load_tests(self):
        with open(self.wp.workdir / self.insn.working_dir / "testcases.json", "r") as f:
            self.set_insn_info(json.load(fp=f))

    def gen_tests(self, binary = None, output_fn = None, filter_fn = lambda x: True):
        def default_output_fn(index, testcase, insn):
            return TempFile(prefix="output_" + insn.insn + "_")

        if binary is None:
            # run the oracle
            binary = self.wp.workdir / self.insn.working_dir / self.insn.insn

        output_fn = output_fn or default_output_fn

        for i, t in filter(filter_fn, enumerate(self.insn_info['tests'])):
            tmp_output = output_fn(i, t, self.insn)

            # TODO: this command-line format doesn't work for all tests, esp. those that execute
            # with multiple threads

            inpfile = Path(t['input'])
            outfile = Path(t['output'])

            if not inpfile.is_absolute():
                inpfile = self.wp.tests_dir / inpfile

            if not outfile.is_absolute():
                outfile = self.wp.tests_dir / outfile

            yield TestInfo(cmdline=[binary, inpfile, tmp_output],
                           tmp_output = tmp_output,
                           gold_output= outfile)

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
