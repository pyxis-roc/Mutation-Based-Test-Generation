#!/usr/bin/env python3
#
# mutate.py
#
# Generates mutated variants on semantics file. Based loosely on
# mutators.py, but restricted in scope to producing mutations only.

import argparse
from pathlib import Path
import os
from build_single_insn import Insn
import subprocess

class MUSICMutator:
    def __init__(self, rootdir, music_executable, fixed_compilation_database = True):
        self.rootdir = Path(rootdir)
        self.music = Path(music_executable)
        self.fixed_compilation_database = fixed_compilation_database

        if not self.music.exists():
            # we require a path since will not use the shell when executing.
            raise FileNotFoundError(f"MUSIC executable not found: {self.music}")

        if not self.rootdir.exists():
            raise FileNotFoundError(f"Root directory does not exist: {self.rootdir}")

    def _get_line_range(self, insn):
        with open(self.rootdir / insn.working_dir / insn.sem_file, "r") as f:
            sm = insn.start_marker
            em = insn.end_marker

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

    def generate_mutations(self, insn):
        start, end = self._get_line_range(insn)
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

        print(" ".join([str(c) for c in cmd]))
        subprocess.run(cmd, check=True)


class MULL:
    pass


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate single instruction tests from the C semantics")
    p.add_argument("rootdir", help="Directory used as root to store oracle files")
    p.add_argument("--mutator", choices=["MUSIC"], default="MUSIC")
    p.add_argument("--music", help="MUSIC executable", default="../../MUSIC/music")

    args = p.parse_args()


    if args.mutator == "MUSIC":
        mut = MUSICMutator(args.rootdir, music_executable = args.music)
    else:
        raise NotImplementedError(f"Do not support mutator {args.mutator}")

    for insn in ['add_rm_ftz_f32']:
        i = Insn(insn)
        mut.generate_mutations(i)
