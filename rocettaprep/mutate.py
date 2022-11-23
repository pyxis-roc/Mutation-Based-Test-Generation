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
from parsl.app.app import python_app
import parsl
import runcommon
from insninfo import insn_info
from collections import namedtuple

MutCoord = namedtuple('MutCoord', 'filename start_line start_col end_line end_col')

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

            # this patches in a faked ptxc_utils.h that avoids Generics.
            # makes MUSIC mutate FTZ again.
            cmd.extend(["-I", Path(__file__).parent / 'include'])

            # TODO: move this to use wp.include_dirs?
            cmd.extend(["-I", self.csemantics.parent])

            # this causes a ton of warnings, but also does not prevent the substitution of _Generic
            # in the code (SMVB?)
            # so disabled.
            #cmd.append("-DPYCPARSER")

        logging.debug(f"Mutate command {' '.join([str(c) for c in cmd])}")
        print(f"Mutate command {' '.join([str(c) for c in cmd])}")

        with open(odir / "MUSIC.output.txt", "w") as outf:
            with open(odir / "MUSIC.errors.txt", "w") as errf:
                #subprocess.run(cmd, check=True, stdout=outf, stderr=errf)
                _, time = runcommon.run_and_time(cmd, check=True, stdout=outf, stderr=errf)
                print(f"Mutation of {insn} took {time/1E6} ms")

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

        with open(odir / "Makefile", "w") as f:
            all_targets = " ".join([s[:-2] for s in srcs])
            f.write("CFLAGS ?= -g -O3\n\n")
            f.write(f"all: {all_targets}\n\n")
            f.write(f".PHONY: clean\n\n")
            f.write(f"clean:\n")
            f.write(f"\trm -f {all_targets}\n\n") # will almost certainly exceed command line limits?

            for s in srcs:
                target = s[:-2] # remove .c
                ss = [str(odir / s)]
                f.write(f"{target}: {' '.join(ss)}\n\t")
                cmds = p.get_compile_command_primitive(s, "../" + insn.test_file,
                                                       target, cflags=["${CFLAGS}",
                                                                       "-Wuninitialized"])

                out.append({'src': str(s), 'target': target})

                f.write("\n\t".join([" ".join([str(cc) for cc in c])
                                     for c in cmds]))
                f.write("\n\n")

        # also write out metadata for other tools to process
        with open(odir.parent / "music.json", "w") as f:
            json.dump(out, fp=f, indent='  ')

class MULL:
    pass

class MUSICHelper:
    srcdir = "music"

    def __init__(self, wp):
        self.wp = wp

    def get_source_coord(self, mutinfo, before = True):
        line_offset = 0

        if before:
            pfx = 'before:'
        else:
            pfx = 'after:'
            # if kill is used, then line_offset = 3
            if "kill" in mutinfo['Mutated Token']:
                line_offset = 3

        return MutCoord(filename = mutinfo['Mutant Filename'],
                        start_line = int(mutinfo[f'{pfx}Start Line#'])+line_offset,
                        start_col = int(mutinfo[f'{pfx}Start Col#']),
                        end_line = int(mutinfo[f'{pfx}End Line#'])+line_offset,
                        end_col = int(mutinfo[f'{pfx}End Col#']),
                        )

    def get_mutation_information(self, insn):
        odir = self.wp.workdir / insn.working_dir / self.srcdir

        n = Path(insn.sem_file).stem + '_mut_db.csv'
        with open((odir / n), "r") as f:

            f.readline() # skip first line, seems to contain a header
                         # that we're not interested in

            d = csv.reader(f)
            headers = None
            out = []
            for row in d:
                if headers is None:
                    headers = row
                    for k in range(2,2+4):
                        headers[k] = "before:" + headers[k]

                    for k in range(7,7+4):
                        headers[k] = "after:" + headers[k]

                    continue

                rd = dict([(k, None) for k in headers])
                rd.update(dict(zip(headers, row)))
                if len(row) > len(headers):
                    rd[None] = row[len(headers):]

                if None in rd:
                    assert len(rd[None]) == 1, rd[None]
                    rd['_function'] = rd[None][0]

                out.append((rd['Mutant Filename'], rd))

            dout = dict(out)
            assert len(dout) == len(out) # duplicates!
            return dout

    def get_mutants(self, insn):
        workdir = self.wp.workdir / insn.working_dir

        with open(workdir / "music.json", "r") as f:
            mutants = json.load(fp=f)

        return mutants

    def get_test_timings(self, insn, experiment, round2 = False, r2source = 'eqvcheck',
                         all_subset = False):
        workdir = self.wp.workdir / insn.working_dir

        if round2:
            if all_subset:
                subset = 'all.'
            else:
                subset = ''

            # from run_mutants_2.py

            fname = workdir / f"mutant_timing.{subset}{experiment}.{r2source}.json"
        else:
            fname = workdir / f"mutant_timing.{experiment}.json"

        with open(fname, "r") as f:
            tests = json.load(fp=f)

        return tests

    def get_survivors(self, insn, experiment, round2 = False, r2source = 'eqvcheck', all_subset = False):
        workdir = self.wp.workdir / insn.working_dir

        if round2:
            if all_subset:
                subset = 'all.'
            else:
                subset = ''

            fname = workdir / f"mutation-testing.round2.{r2source}.{subset}{experiment}.json"
        else:
            fname = workdir / f"mutation-testing.{experiment}.json"

        with open(fname, "r") as f:
            survivors = json.load(fp=f)

        return survivors

    def save_survivors(self, insn, experiment, survivors):
        with open(self.wp.workdir / insn.working_dir / f"mutation-testing.{experiment}.json", "w") as f:
            json.dump(survivors, fp=f, indent='  ')


def get_mutation_helper(mutator, wp):
    if mutator == "MUSIC":
        return MUSICHelper(wp)
    else:
        raise NotImplementedError(f"Support for {mutator} not yet implemented")

def get_mutators():
    return ["MUSIC"]

@python_app
def run_mutator(mut, i):
    mut.generate_mutations(i)
    mut.generate_mutation_makefile(i)

if __name__ == "__main__":
    from setup_workdir import WorkParams
    from runconfig import config

    p = argparse.ArgumentParser(description="Generate single instruction tests from the C semantics")
    p.add_argument("workdir", help="Work directory")
    p.add_argument("--mutator", choices=get_mutators(), default="MUSIC")
    p.add_argument("--music", help="MUSIC executable", default="../../MUSIC/music")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")

    args = p.parse_args()
    wp = WorkParams.load_from(args.workdir)

    parsl.load(config)

    if args.mutator == "MUSIC":
        mut = MUSICMutator(wp.csemantics, wp.workdir, music_executable = args.music)
    else:
        raise NotImplementedError(f"Do not support mutator {args.mutator}")

    out = []
    for insn in get_instructions(args.insn):
        i = Insn(insn, insn_info[insn])
        out.append(run_mutator(mut, i))

    for x in out: x.result()
