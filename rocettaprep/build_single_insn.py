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
import logging
from rocprepcommon import *

logger = logging.getLogger(__name__)

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
        print(f"cpp_args: '{' '.join([str(c) for c in cpp_args])}'")

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
        os.unlink(t)

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

    def get_func_code(self, insn_fn):
        assert insn_fn in self.funcdef_nodes, f"{insn_fn} not found in {self.csemantics}"

        generator = c_generator.CGenerator()
        func_code = generator.visit(self.funcdef_nodes[insn_fn])

        return func_code

    def create_single_insn_program(self, insn, sys_includes = [], user_includes = []):
        insn_fn = insn.insn_fn

        func_code = self.get_func_code(insn_fn)

        out = []
        out.extend([f'#include <{x}>' for x in sys_includes])
        out.extend([f'#include "{x}"' for x in user_includes])

        out.append(insn.start_marker)
        out.append(func_code)
        out.append(insn.end_marker)

        return '\n'.join(out) + '\n'

    def create_single_insn_test_program(self, insn, dstdir):
        # this is old style
        test_program = self.csemantics.parent / insn.test_file
        dst = dstdir / insn.test_file

        shutil.copyfile(test_program, dst)

    def get_compile_command_primitive(self, semc, testc, outputobj, compiler_cmd = None, libs = None, cflags = None):

        def default_compiler(srcfiles, obj, cflags, libs):
            cmd = ["gcc"]
            cmd.extend(cflags)
            cmd.extend(["-I", self.csemantics.parent.absolute()])
            cmd.extend(filter(lambda x: x is not None, srcfiles))
            cmd.extend(["-o", obj])
            cmd.extend(libs)
            return cmd

        compiler_cmd = compiler_cmd or default_compiler
        libs = libs or ["-lm"]
        cflags = cflags or []
        cmds = []
        cmds.append(compiler_cmd([f"{self.csemantics.parent.absolute()}/testutils.c", semc, testc],
                                 outputobj, cflags, libs))
        return cmds

    def get_compile_command(self, insn, obj = None):
        obj = obj or insn

        return self.get_compile_command_primitive(insn.sem_file, insn.test_file, str(insn))

class Insn:
    def __init__(self, insn):
        self.insn = insn

    @property
    def working_dir(self):
        return f'working-directory-{self.insn}'

    @property
    def sem_file(self):
        return f'{self.insn}_fn.c'

    @property
    def test_file(self):
        return f'{self.insn}.c'

    @property
    def insn_fn(self):
        return f'execute_{self.insn}'

    @property
    def start_marker(self):
        return f'// START: {self.insn_fn}'

    @property
    def end_marker(self):
        return f'// END: {self.insn_fn}'

    def __str__(self):
        return self.insn

    def get_line_range(self, src):

        # the original code in mutator.py for the registered report
        # had an off-by-one error that caused MUSIC not to mutate the
        # last line of the semantics.
        #
        # for example: music on abs_f32 yields 95 mutants with this
        # code, but only 70 with the original code.

        with open(src, "r") as f:
            sm = self.start_marker
            em = self.end_marker

            start = -1
            end = -1

            for i, l in enumerate(f, 1):
                if l.startswith(sm):
                    start = i
                    break
            else:
                raise ValueError(f"Start marker {sm} not found in {f.name}")


            for i, l in enumerate(f, 1):
                if l.startswith(em):
                    end = i
                    break
            else:
                raise ValueError(f"End marker {em} not found in {f.name}")

            assert start != -1 and end != -1

            return start, end

def gen_insn_oracle(insn, oroot, p):
    insn = Insn(insn)

    odir = oroot / insn.working_dir
    if not odir.exists():
        odir.mkdir()

    code = p.create_single_insn_program(insn,
                                        ['stdlib.h', 'stdint.h', 'math.h'],
                                        hdrs)

    with open(odir / insn.sem_file, "w") as f:
        f.write(code)

    p.create_single_insn_test_program(insn, odir)
    with open(odir / "Makefile", "w") as f:
        f.write(f"{insn}: {insn.test_file}\n\t")
        compile_cmds = "\n\t".join([" ".join([str(x) for x in c]) for c in p.get_compile_command(insn)])
        f.write(compile_cmds + "\n")

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Generate single instruction tests from the C semantics")
    p.add_argument("workdir", help="Work directory")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")

    args = p.parse_args()
    insns = get_instructions(args.insn)

    if len(insns):
        wp = WorkParams.load_from(args.workdir)

        p = PTXSemantics(wp.csemantics, [wp.pycparser_includes] + wp.include_dirs)
        p.parse()
        p.get_functions()
        hdrs = p.get_headers()

        oroot = Path(args.workdir)

        for insn in insns:
            gen_insn_oracle(insn, oroot, p)

    print(f"{len(insns)} instructions processed.")
