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

    def process_mutfile(self, mutfile):
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


def load_music_json(rootdir, insn):
    mj = rootdir / insn.working_dir / "music.json"

    with open(mj, "r") as f:
        muts = json.load(fp=f)
        return list([rootdir / insn.working_dir / "music" / x['src'] for x in muts])

def build_eqvcheck_driver(csemantics, rootdir, mutator, insn, include_dirs, setup_only = False):
    if mutator != "MUSIC":
        raise NotImplementedError(f"Don't know how to build equivalence checker for {mutator}")

    mutsrcs = load_music_json(rootdir, insn)
    cs = Path(csemantics)
    ecb = EqvCheckBuilder(csemantics, rootdir, insn, include_dirs)
    ecb.setup()
    if not setup_only:
        for s in mutsrcs:
            print(s)
            ecb.process_mutfile(s)

    #print(mutsrcs)

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Build the driver for equivalence checks")
    p.add_argument("workdir", help="Root working directory")
    p.add_argument("--mutator", choices=["MUSIC"], default="MUSIC")
    p.add_argument("--driver-only", action="store_true", help="Only generate the driver")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")

    args = p.parse_args()
    wp = WorkParams.load_from(args.workdir)
    incl = [wp.pycparser_includes] + wp.include_dirs

    for insn in get_instructions(args.insn):
        print(insn)
        i = Insn(insn)
        build_eqvcheck_driver(wp.csemantics, wp.workdir, args.mutator, i, incl, args.driver_only)
