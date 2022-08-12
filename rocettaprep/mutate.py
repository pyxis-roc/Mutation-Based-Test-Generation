#!/usr/bin/env python3
#
# mutate.py
#
# Generates mutated variants on semantics file. Based loosely on
# mutators.py, but restricted in scope to producing mutations only.

import argparse
from pathlib import Path
import os
from build_single_insn import Insn, PTXSemantics
import subprocess
import csv
import json
import logging
from rocprepcommon import *

logger = logging.getLogger(__name__)

class MUSICMutator:
    def __init__(self, csemantics, rootdir, music_executable, fixed_compilation_database = True):
        self.csemantics = csemantics
        self.rootdir = Path(rootdir)
        self.music = Path(music_executable)
        self.fixed_compilation_database = fixed_compilation_database

        if not self.music.exists():
            # we require a path since will not use the shell when executing.
            raise FileNotFoundError(f"MUSIC executable not found: {self.music}")

        if not self.rootdir.exists():
            raise FileNotFoundError(f"Root directory does not exist: {self.rootdir}")

    def generate_mutations(self, insn):
        start, end = insn.get_line_range(self.rootdir / insn.working_dir / insn.sem_file)
        odir = self.rootdir / insn.working_dir / "music"

        if not odir.exists():
            odir.mkdir()

        sem_file = odir.parent / insn.sem_file

        # the -- indicates a fixed compilation database which kinda works
        # Experiments with compile_commands.json seem to work but no particular
        # advantange?

        cmd = [self.music, sem_file, "-o", odir,
               "-rs", f"{sem_file}:{start}", "-re", f"{sem_file}:{end}"]

        if self.fixed_compilation_database:
            # TODO: maybe add some compile commands as well
            cmd.append("--")

        logging.debug(f"Mutate command {' '.join([str(c) for c in cmd])}")
        subprocess.run(cmd, check=True)

    def _get_mutated_sources(self, odir, insn):
        n = Path(insn.sem_file).stem + '_mut_db.csv'
        with open((odir / n), "r") as f:

            f.readline() # skip first line, seems to contain a header
                         # that we're not interested in

            d = csv.DictReader(f)
            out = []
            for row in d:
                out.append(row['Mutant Filename'])

            return out

    def generate_mutation_makefile(self, insn):
        odir = self.rootdir / insn.working_dir / "music"
        srcs = self._get_mutated_sources(odir, insn)

        p = PTXSemantics(self.csemantics, []) # since we only want the compiler commands

        out = []

        with open(odir.parent / "Makefile.music", "w") as f:
            all_targets = " ".join([s[:-2] for s in srcs])
            f.write(f"all: {all_targets}\n\n")

            for s in srcs:
                target = s[:-2] # remove .c
                srcs = [str(odir / s)]
                f.write(f"{target}: {' '.join(srcs)}\n\t")
                cmds = p.get_compile_command_primitive(str(odir / s), insn.test_file,
                                                       target)

                out.append({'src': str(s), 'target': target})

                f.write("\n\t".join([" ".join([str(cc) for cc in c])
                                     for c in cmds]))
                f.write("\n\n")

        # also write out metadata for other tools to process
        with open(odir.parent / "music.json", "w") as f:
            json.dump(out, fp=f, indent='  ')

class MULL:
    pass


if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Generate single instruction tests from the C semantics")
    p.add_argument("workdir", help="Work directory")
    p.add_argument("--mutator", choices=["MUSIC"], default="MUSIC")
    p.add_argument("--music", help="MUSIC executable", default="../../MUSIC/music")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")

    args = p.parse_args()
    wp = WorkParams.load_from(args.workdir)

    if args.mutator == "MUSIC":
        mut = MUSICMutator(wp.csemantics, wp.workdir, music_executable = args.music)
    else:
        raise NotImplementedError(f"Do not support mutator {args.mutator}")

    for insn in get_instructions(args.insn):
        i = Insn(insn)
        mut.generate_mutations(i)
        mut.generate_mutation_makefile(i)
