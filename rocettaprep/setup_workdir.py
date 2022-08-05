#!/usr/bin/env python3
#
# setup_workdir.py
#
# Setup the directory for performing mutation-based test
# generation. Saves having to type lots of parameters repeatedly.

import argparse
from pathlib import Path
import json
import itertools
import sys
from build_single_insn import PTXSemantics
from pycparser import parse_file, c_ast, c_generator

class WorkParams:
    def __init__(self):
        self.workdir = None
        self.csemantics = None
        self.pycparser_includes = None
        self.include_dirs = None

    @property
    def all_includes(self):
        return [self.pycparser_includes] + self.include_dirs

    @staticmethod
    def load_from(directory):
        with open(Path(directory) / "params.json", "r") as f:
            p = json.load(fp=f)
            wp = WorkParams()

            for path_param in ['workdir', 'csemantics',
                               'pycparser_includes',
                               'include_dirs']:

                if isinstance(p[path_param], list):
                    setattr(wp, path_param, [Path(x) for x in p[path_param]])
                else:
                    setattr(wp, path_param, Path(p[path_param]))

                del p[path_param]

            assert len(p) == 0, f"Internal error: Unhandled parameters: {p}"

            return wp

    def save(self):
        with open(self.workdir / "params.json", "w") as f:
            x = {}
            for path_param in ['workdir', 'csemantics',
                               'pycparser_includes',
                               'include_dirs']:

                v = getattr(self, path_param)

                if isinstance(v, list):
                    x[path_param] = [str(xx) for xx in v]
                else:
                    x[path_param] = str(v)

            p = json.dump(x, fp=f, indent='  ')


class TypedefVisitor(c_ast.NodeVisitor):
    def __init__(self, filename):
        self.td = []
        self.filename = filename

    def visit_Typedef(self, node):
        if node.coord.file == self.filename:
            self.td.append(node)

def create_ptx_semantics_fake_includes(wp):
    ps = PTXSemantics(wp.csemantics, wp.all_includes)
    includes = ps.get_headers()
    hdrs = includes + list(ps.EXCLUDE_INDIRECT)
    generator = c_generator.CGenerator()

    fid = wp.workdir / 'ptxc_fake_includes'
    if not fid.exists():
        fid.mkdir()

    for h in hdrs:
        ast = parse_file(wp.csemantics.parent / h,
                         use_cpp = True, cpp_path='cpp', cpp_args = ps._get_cpp_args())

        tdv = TypedefVisitor(str(wp.csemantics.parent / h))
        tdv.visit(ast)

        if len(tdv.td):
            with open(fid / h, "w") as f:
                for td in tdv.td:
                    print(generator.visit(td) + ";", file=f)

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Setup a work directory")
    p.add_argument("csemantics", help="C Semantics File")
    p.add_argument("workdir", help="Directory to setup, will be created if it does not exist")

    p.add_argument("--fake-includes", help="Path to pycparser stub includes",
                   default="/usr/share/python3-pycparser/fake_libc_include/") # this default is good for most Debian-based machines
    p.add_argument("-I", dest="include_dirs", help="Include directory for preprocessor", action="append", default=[])


    args = p.parse_args()

    wp = WorkParams()
    wp.csemantics = Path(args.csemantics).absolute()
    wp.workdir = Path(args.workdir).absolute()
    wp.pycparser_includes = Path(args.fake_includes).absolute()
    wp.include_dirs = [Path(p).absolute() for p in args.include_dirs]

    if not wp.csemantics.exists():
        raise FileNotFoundError(f"C semantics file: {wp.csemantics} not found")

    if not wp.workdir.exists():
        wp.workdir.mkdir()

    for d in itertools.chain([wp.pycparser_includes], wp.include_dirs):
        if not d.exists():
            print("WARNING: Include directory {d} does not exist (check --fake-includes or -I)", file=sys.stderr)

    create_ptx_semantics_fake_includes(wp)
    wp.save()
    print("Setup done")
