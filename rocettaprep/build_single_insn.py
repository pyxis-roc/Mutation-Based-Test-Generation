#!/usr/bin/env python3
#
# build_single_insn.py
#
# Extracts single instruction tests from the C semantics. Based on
# program_manipulation.py, but decoupled and specialized to the PTX
# semantics.


import argparse
from pycparser import parse_file
import subprocess
import tempfile
from pathlib import Path
import os

class PTXSemantics:
    EXCLUDE_INDIRECT = {'ptxc_utils_template.h', '128types.h'}

    def __init__(self, csemantics, include_dirs, cpp='cpp'):
        self.csemantics = Path(csemantics)
        self.include_dirs = include_dirs
        self.cpp = cpp

    def _get_cpp_args(self):
        cpp_args = ["-DPYCPARSER"] # this is to "hide" C99 constructs like _Generic
        cpp_args.append('-D__STDC_VERSION__=199901L')
        cpp_args.extend([f"-I{x}" for x in self.include_dirs if x])
        return cpp_args

    def parse(self):
        parse_file(self.csemantics, use_cpp=True, cpp_path=self.cpp,
                   cpp_args = self._get_cpp_args())

    def get_headers(self):
        # use the C preprocessor to extract include files
        # use a tempfile to avoid debug output
        h, t = tempfile.mkstemp()
        os.close(h)

        subprocess.run([self.cpp] + self._get_cpp_args() + ["-MM", "-MF", t, self.csemantics], check=True)
        headers = ''.join(open(t, "r").readlines())
        headers = headers.replace('\\\n', '\n')

        # parse the output
        target = self.csemantics.stem + '.o:'
        assert headers.startswith(target), headers
        headers = headers[len(target):].strip().split() # will have issues with spaces in paths
        headers = [Path(x) for x in headers]

        # keep only those in the same directory
        prefix = self.csemantics.parent
        headers = [x.name for x in headers if x != self.csemantics and x.parent == prefix and x.name not in self.EXCLUDE_INDIRECT]
        return headers

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate single instruction tests from the C semantics")
    p.add_argument("csemantics", help="C semantics file, usually ptxc.c")
    p.add_argument("--fake-includes", help="Path to pycparser stub includes", default="/usr/share/python3-pycparser/fake_libc_include/") # this default is good for most Debian-based machines
    p.add_argument("-I", dest="include_dirs", help="Include directory for preprocessor", action="append", default=[])

    args = p.parse_args()

    p = PTXSemantics(args.csemantics, [args.fake_includes] + args.include_dirs)
    #p.parse()
    print(p.get_headers())
