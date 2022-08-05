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

    def process_mutfile(self, mutfile):
        ps = PTXSemantics(mutfile, self.include_dirs + [self.rootdir / 'ptxc_fake_includes',
                                                        self.csemantics.parent])
        ps.parse()
        ps.get_functions()

        # TODO: rename function
        code = ps.get_func_code(self.insn.insn_fn)
        print(code)


def load_music_json(rootdir, insn):
    mj = rootdir / insn.working_dir / "music.json"

    with open(mj, "r") as f:
        muts = json.load(fp=f)
        return list([rootdir / insn.working_dir / "music" / x['src'] for x in muts])

def build_eqvcheck_driver(csemantics, rootdir, mutator, insn, include_dirs):
    if mutator != "MUSIC":
        raise NotImplementedError(f"Don't know how to build equivalence checker for {mutator}")

    mutsrcs = load_music_json(rootdir, insn)
    cs = Path(csemantics)
    ecb = EqvCheckBuilder(csemantics, rootdir, insn, include_dirs)
    ecb.setup()
    for s in mutsrcs:
        ecb.process_mutfile(s)

    print(mutsrcs)

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Build the driver for equivalence checks")
    p.add_argument("workdir", help="Root working directory")
    p.add_argument("--mutator", choices=["MUSIC"], default="MUSIC")

    args = p.parse_args()
    wp = WorkParams.load_from(args.workdir)
    incl = [wp.pycparser_includes] + wp.include_dirs

    for insn in ['add_rm_ftz_f32']:
        i = Insn(insn)
        build_eqvcheck_driver(wp.csemantics, wp.workdir, args.mutator, i, incl)
