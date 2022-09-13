#!/usr/bin/env python

import argparse
import subprocess
from pathlib import Path
import sys

MYPATH = Path(__file__).parent.absolute()

def run_and_log(cmd, logfile):
    with open(logfile, "w") as f:
        print('Running', ' '.join(cmd), file=sys.stderr)
        print('Logging to', logfile)
        subprocess.run(cmd, check=True, stdout=f, stderr=f)

class Orchestrator:
    def __init__(self, workdir, experiment, insn, logdir, mutator = 'MUSIC', serial = False):
        self.workdir = workdir
        self.experiment = experiment
        self.insn = insn
        self.logdir = logdir
        self.mutator = mutator
        self.serial = serial
        if self.mutator != 'MUSIC':
            raise NotImplementedError(f'Do not support non-MUSIC mutators yet')

    def run_mutants(self):
        print(f"*** BEGINNING run_mutants")
        cmd = [str(MYPATH / 'run_mutants.py'), '--insn', self.insn, self.workdir, self.experiment]
        logfile = self.logdir / 'music_mutants.log'
        run_and_log(cmd, logfile)

    def run_round2(self, r2source):
        print(f"*** BEGINNING round2 on {r2source}")
        print(MYPATH, MYPATH / 'run_mutants.py')
        cmd = [str(MYPATH / 'run_mutants.py'), '--insn', self.insn,
               '--round2',
               '--r2source', r2source,
               self.workdir, self.experiment]

        logfile = self.logdir / f'round2.{r2source}.log'
        run_and_log(cmd, logfile)

    def run_fuzzer(self, fuzzer, run_all=False):
        print(f"*** BEGINNING fuzzer {fuzzer}")
        cmd = [str(MYPATH / 'run_fuzzer.py'),
               '--mutator', self.mutator,
               '--insn', self.insn,
               '--fuzzer', fuzzer]

        note = []
        if run_all:
            cmd.append('--all')
            note.append('.all')

        if self.serial:
            cmd.append('--np')
            note.append('.serial')

        note = ''.join(note)
        cmd.extend([self.workdir, self.experiment])
        logfile = self.logdir / f'fuzzer.{fuzzer}{note}.log'

        run_and_log(cmd, logfile)

    def run_eqvcheck(self, run_all = False):
        print(f"*** BEGINNING eqvcheck")
        cmd = [str(MYPATH / 'run_eqvcheck.py'),
               '--mutator', self.mutator,
               '--insn', self.insn]

        note = []
        if run_all:
            cmd.append('--all')
            note.append('.all')

        if self.serial:
            cmd.append('--np')
            note.append('.serial')

        note = ''.join(note)
        cmd.extend([self.workdir, self.experiment])
        logfile = self.logdir / f'eqvcheck{note}.log'

        run_and_log(cmd, logfile)

    def run_gather_witnesses(self):
        print(f"*** BEGINNING run_gather_witnesses")
        cmd = [str(MYPATH / 'run_gather_witnesses.py'),
               '--insn', self.insn,
               self.workdir, self.experiment]

        logfile = self.logdir / f'gather_witnesses.log'
        run_and_log(cmd, logfile)

    def run_collect_fuzzer(self, fuzzer):
        print(f"*** BEGINNING collect_fuzzer {fuzzer}")
        cmd = [str(MYPATH / 'run_collect_fuzzer.py'),
               '--insn', self.insn,
               '--mutator', self.mutator,
               '--fuzzer', fuzzer,
               self.workdir, self.experiment]

        #TODO: This does not distinguish between --all runs?
        logfile = self.logdir / f'collect_fuzzer.{fuzzer}.log'
        run_and_log(cmd, logfile)

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Orchestrate a run of experiments")
    p.add_argument("workdir", help="Working directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")
    p.add_argument("--all", help="Run on all mutants", action='store_true')
    p.add_argument("--no-parallel", help="Run everything serially", action='store_true')

    args = p.parse_args()

    wp = WorkParams.load_from(args.workdir)
    logdir = Path(wp.workdir / f'expt.{args.experiment}')

    if not logdir.exists():
        logdir.mkdir()

    x = Orchestrator(args.workdir, args.experiment, args.insn, logdir, serial=args.no_parallel)

    x.run_mutants()
    x.run_eqvcheck()
    x.run_fuzzer('simple', run_all = args.all)
    x.run_fuzzer('custom', run_all = args.all)

    x.run_gather_witnesses()
    x.run_collect_fuzzer('simple')
    x.run_collect_fuzzer('custom')

    x.run_round2('eqvcheck')
    x.run_round2('fuzzer_simple')
    x.run_round2('fuzzer_custom')
