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
import shutil

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

    def create_single_insn_program(self, insn, sys_includes = [], user_includes = []):
        insn_fn = f'execute_{insn}'

        assert insn_fn in self.funcdef_nodes, f"{insn_fn} not found in {self.csemantics}"

        generator = c_generator.CGenerator()
        func_code = generator.visit(self.funcdef_nodes[insn_fn])

        out = []
        out.extend([f'#include <{x}>' for x in sys_includes])
        out.extend([f'#include "{x}"' for x in user_includes])

        out.append(f'// START: {insn_fn}')
        out.append(func_code)
        out.append(f'// END: {insn_fn}')

        return '\n'.join(out) + '\n'

    def create_single_insn_test_program(self, insn, dstdir):
        # this is old style
        test_program = self.csemantics.parent / (insn + '.c')
        dst = dstdir / (insn + '.c')

        shutil.copyfile(test_program, dst)

    def get_compile_command_primitive(self, semc, testc, outputobj, compiler_cmd = None, libs = None):
        def default_compiler(srcfiles, obj):
            cmd = ["gcc"]
            cmd.extend(["-I", self.csemantics.parent.absolute()])
            cmd.extend(srcfiles)
            cmd.extend(["-o", insn])
            cmd.extend(libs)
            return cmd

        compiler_cmd = compiler_cmd or default_compiler
        libs = libs or ["-lm"]

        cmds = []
        cmds.append(compiler_cmd([f"{self.csemantics.parent.absolute()}/testutils.c", semc, testc], outputobj))
        return cmds

    def get_compile_command(self, insn, obj = None):
        obj = obj or insn

        return self.get_compile_command_primitive(f"{insn}_fn.c", f"{insn}.c", insn)

def gen_insn_oracle(insn, oroot, p):
    odir = oroot / f'working-directory-{insn}'
    if not odir.exists():
        odir.mkdir()

    code = p.create_single_insn_program(insn,
                                        ['stdlib.h', 'stdint.h', 'math.h'],
                                        hdrs)

    # the name _fn.c is part of the API, ...
    with open(odir / f'{insn}_fn.c', "w") as f:
        f.write(code)

    p.create_single_insn_test_program(insn, odir)
    with open(odir / "Makefile", "w") as f:
        f.write(f"{insn}: {insn}.c\n\t")
        compile_cmds = "\n\t".join([" ".join([str(x) for x in c]) for c in p.get_compile_command(insn)])
        f.write(compile_cmds + "\n")

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
        gen_insn_oracle(insn, oroot, p)
