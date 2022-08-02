#!/usr/bin/env python3
#
# build_single_insn.py
#
# Extracts single instruction tests from the C semantics. Based on
# program_manipulation.py, but decoupled and specialized to the PTX
# semantics.


import argparse
from pycparser import parse_file, c_ast, c_generator
import subprocess
import tempfile
from pathlib import Path
import os
from collections import OrderedDict

class FuncDefVisitor(c_ast.NodeVisitor):
    def __init__(self):
        self.fd_nodes = OrderedDict()

    def visit_FuncDef(self, node):
        self.fd_nodes[node.decl.name] = node

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
        self.ast = parse_file(self.csemantics, use_cpp=True, cpp_path=self.cpp,
                              cpp_args = self._get_cpp_args())

    def get_functions(self):
        v = FuncDefVisitor()
        v.visit(self.ast)
        self.funcdef_nodes = v.fd_nodes
        return self.funcdef_nodes

    def get_headers(self):
        # use the C preprocessor to extract include files
        # use a tempfile to avoid debug output
        h, t = tempfile.mkstemp()
        os.close(h)

        subprocess.run([self.cpp] + self._get_cpp_args() + ["-MM", "-MF", t, self.csemantics], check=True)
        headers = ''.join(open(t, "r").readlines())
        headers = headers.replace('\\\n', '\n')

        # parse the output which is formatted as a Make rule
        target = self.csemantics.stem + '.o:'
        assert headers.startswith(target), headers
        headers = headers[len(target):].strip().split() # will have issues with spaces in paths
        headers = [Path(x) for x in headers]

        # keep only those in the same directory
        prefix = self.csemantics.parent
        headers = [x.name for x in headers if x != self.csemantics and x.parent == prefix and x.name not in self.EXCLUDE_INDIRECT]

        self.headers = headers
        return self.headers

    def create_single_insn_program(self, insn_fn, sys_includes = [], user_includes = []):
        assert insn_fn in self.funcdef_nodes, f"{insn_fn} not found in {self.csemantics}"

        generator = c_generator.CGenerator()
        func_code = generator.visit(self.funcdef_nodes[insn_fn])

        out = []
        out.extend([f'#include <{x}>' for x in sys_includes])
        out.extend([f'#include "{x}"' for x in user_includes])

        out.append(f'// START: {insn_fn}')
        out.append(func_code)
        out.append(f'// END: {insn_fn}')

        return '\n'.join(out)

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate single instruction tests from the C semantics")
    p.add_argument("csemantics", help="C semantics file, usually ptxc.c")
    p.add_argument("outputdir", help="Output directory, will be created if it does not exist")

    p.add_argument("--fake-includes", help="Path to pycparser stub includes", default="/usr/share/python3-pycparser/fake_libc_include/") # this default is good for most Debian-based machines
    p.add_argument("-I", dest="include_dirs", help="Include directory for preprocessor", action="append", default=[])

    args = p.parse_args()

    if not os.path.exists(args.outputdir):
        os.mkdir(args.outputdir)

    p = PTXSemantics(args.csemantics, [args.fake_includes] + args.include_dirs)
    p.parse()
    p.get_functions()
    hdrs = p.get_headers()

    oroot = Path(args.outputdir)

    for insn in ['add_rm_ftz_f32']:
        odir = oroot / f'working-directory-{insn}'
        if not odir.exists():
            odir.mkdir()

        code = p.create_single_insn_program(f'execute_{insn}',
                                            ['stdlib.h', 'stdint.h', 'math.h'],
                                            hdrs)

        with open(odir / f'{insn}.c', "w") as f:
            f.write(code)
