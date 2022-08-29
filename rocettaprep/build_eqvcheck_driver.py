#!/usr/bin/env python3
#
# build_eqvcheck_driver.py
#
# Build the driver for equivalence checking of semantics vs mutated
# function.
#

from build_single_insn import Insn, PTXSemantics
from pycparser import c_ast, c_generator
import argparse
from pathlib import Path
import os
import json
import shutil
from eqvcheck_templates import EqvCheckTemplate
from rocprepcommon import *
from mutate import get_mutation_helper, get_mutators
from parsl.app.app import python_app
from parsl.configs.local_threads import config
import parsl
import sys

parsl.load(config)

class EqvCheckBuilder:
    def __init__(self, csemantics, rootdir, insn, include_dirs = None):
        self.csemantics = Path(csemantics)
        self.rootdir = Path(rootdir)
        self.insn = insn
        self.include_dirs = include_dirs or []

    def setup(self):
        semfile = self.rootdir / self.insn.working_dir / self.insn.sem_file
        with open(semfile, "r") as f:
            self.semfile_contents = f.readlines()

        odir = semfile.parent / "eqchk"

        if not odir.exists():
            odir.mkdir()

        # generate driver
        tmpl = EqvCheckTemplate(self.insn, "mutated_fn")

        with open(odir / self.insn.test_file, "w") as f:
            f.write("\n".join(tmpl.get_decls()))
            f.write(tmpl.get_template())

    def process_mutfile_2(self, mutfile):
        # original version that parses stuff, but breaks for some features

        ps = PTXSemantics(mutfile, self.include_dirs + [self.rootdir / 'ptxc_fake_includes',
                                                        self.csemantics.parent])
        ps.parse()
        ps.get_functions()

        # TODO: rename function via AST rewrite
        code = ps.get_func_code(self.insn.insn_fn)
        code = code.replace(self.insn.insn_fn, "mutated_fn") # should really do a AST rewrite!

        dst = self.rootdir / self.insn.working_dir / "eqchk" / mutfile.name

        shutil.copy(self.rootdir / self.insn.working_dir / self.insn.sem_file,
                    dst)

        with open(dst, "a") as f:
            f.write(code)
            f.write(f"\n#include \"{self.insn.test_file}\"")

    def process_mutfile(self, mutfile):
        with open(mutfile, "r") as f:
            code = "".join([l for l in f if not l.startswith('#include')])

        code = code.replace(self.insn.insn_fn, "mutated_fn") # should really do a AST rewrite!

        dst = self.rootdir / self.insn.working_dir / "eqchk" / mutfile.name

        shutil.copy(self.rootdir / self.insn.working_dir / self.insn.sem_file,
                    dst)

        with open(dst, "a") as f:
            f.write(code)
            f.write(f"\n#include \"{self.insn.test_file}\"")

@python_app
def run_process_mutfile(ecb, mutsrc):
    ecb.process_file(mutsrc)
    return mutsrc

def build_eqvcheck_driver(csemantics, rootdir, muthelper, insn, include_dirs, setup_only = False, parallel = True):
    mutants = muthelper.get_mutants(insn)
    mutsrcs = [rootdir / insn.working_dir / muthelper.srcdir / x['src'] for x in mutants]

    cs = Path(csemantics)
    ecb = EqvCheckBuilder(csemantics, rootdir, insn, include_dirs)
    ecb.setup()
    if not setup_only:
        out = []
        for s in mutsrcs:
            if parallel:
                out.append(run_process_mutfile(ecb, s))
            else:
                print(s, file=sys.stderr)
                ecb.process_mutfile(s)

        if parallel:
            for x in out:
                print(x.result(), file=sys.stderr)

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Build the driver for equivalence checks")
    p.add_argument("workdir", help="Root working directory")
    p.add_argument("--mutator", choices=get_mutators(), default="MUSIC")
    p.add_argument("--driver-only", action="store_true", help="Only generate the driver")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")
    p.add_argument("--np", dest='no_parallel', help="Process serially", action="store_true")

    args = p.parse_args()
    wp = WorkParams.load_from(args.workdir)
    muthelper = get_mutation_helper(args.mutator, wp)

    incl = [wp.pycparser_includes] + wp.include_dirs

    # we process each instruction serially, which is fine, since each instruction has many mutants.

    for insn in get_instructions(args.insn):
        print(insn, file=sys.stderr)
        i = Insn(insn)
        build_eqvcheck_driver(wp.csemantics, wp.workdir, muthelper, i, incl, args.driver_only, parallel=args.no_parallel)
