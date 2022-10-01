#!/usr/bin/env python

import argparse
import subprocess
from pathlib import Path
import sys
import datetime
import os

MYPATH = Path(__file__).parent.absolute()

if False:
    RUN_MUTANTS = 'run_mutants.py'
    RUN_EQVCHECK = 'run_eqvcheck.py'
    RUN_FUZZER = 'run_fuzzer.py'
else:
    RUN_MUTANTS = 'run_mutants_2.py'
    RUN_EQVCHECK = 'run_eqvcheck_2.py'
    RUN_FUZZER = 'run_fuzzer_2.py'

def run_and_log(cmd, logfile):
    with open(logfile, "w") as f:
        print('Running', ' '.join(cmd), file=sys.stderr)
        print('Logging to', logfile)
        subprocess.run(cmd, check=True, stdout=f, stderr=f)

class Orchestrator:
    def __init__(self, workdir, experiment, insn, logdir, mutator = 'MUSIC', serial = False, timeout_s = 90):
        self.workdir = workdir
        self.experiment = experiment
        self.insn = insn
        self.logdir = logdir
        self.mutator = mutator
        self.serial = serial
        self.timeout_s = timeout_s

        if self.mutator != 'MUSIC':
            raise NotImplementedError(f'Do not support non-MUSIC mutators yet')

    def _begin(self, msg):
        print(f"*** BEGINNING {msg} {datetime.datetime.now()}")

    def run_mutants(self):
        self._begin(f"run_mutants")
        cmd = [str(MYPATH / RUN_MUTANTS), '--insn', self.insn, self.workdir, self.experiment]
        logfile = self.logdir / 'music_mutants.log'
        run_and_log(cmd, logfile)

    def run_round2(self, r2source):
        self._begin(f"round2 on {r2source}")
        cmd = [str(MYPATH / RUN_MUTANTS), '--insn', self.insn,
               '--round2',
               '--r2source', r2source,
               self.workdir, self.experiment]

        logfile = self.logdir / f'round2.{r2source}.log'
        run_and_log(cmd, logfile)

    def run_fuzzer(self, fuzzer, run_all=False):
        self._begin(f"fuzzer {fuzzer}")
        cmd = [str(MYPATH / RUN_FUZZER),
               '--mutator', self.mutator,
               '--insn', self.insn,
               '--timeout', str(self.timeout_s),
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
        self._begin(f"eqvcheck")
        cmd = [str(MYPATH / RUN_EQVCHECK),
               '--timeout', str(self.timeout_s),
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
        self._begin(f"run_gather_witnesses")
        cmd = [str(MYPATH / 'run_gather_witnesses.py'),
               '--insn', self.insn,
               self.workdir, self.experiment]

        logfile = self.logdir / f'gather_witnesses.log'
        run_and_log(cmd, logfile)

    def run_collect_fuzzer(self, fuzzer):
        self._begin(f"collect_fuzzer {fuzzer}")
        cmd = [str(MYPATH / 'run_collect_fuzzer.py'),
               '--insn', self.insn,
               '--mutator', self.mutator,
               '--fuzzer', fuzzer,
               self.workdir, self.experiment]

        #TODO: This does not distinguish between --all runs?
        logfile = self.logdir / f'collect_fuzzer.{fuzzer}.log'
        run_and_log(cmd, logfile)

    def gather_mutant_stats(self):
        self._begin(f"gather_mutant_stats")
        cmd = [str(MYPATH / 'stats_mutants.py'),
               '--insn', self.insn,
               '-o', str(self.logdir / f'stats_mutants.{self.experiment}.csv'),
               self.workdir, self.experiment]

        #TODO: This does not distinguish between --all runs?
        logfile = self.logdir / f'mutant_stats.log'
        run_and_log(cmd, logfile)

    def gather_survivor_stats(self):
        self._begin(f"gather_survivor_stats")
        cmd = [str(MYPATH / 'stats_survivors.py'),
               '--insn', self.insn,
               '-o', str(self.logdir / f'stats_survivors.{self.experiment}.txt'),
               self.workdir, self.experiment]

        logfile = self.logdir / f'survivor_stats.log'
        run_and_log(cmd, logfile)

    def gather_input_stats(self):
        self._begin(f"gather_input_stats")
        cmd = [str(MYPATH / 'stats_inputs.py'),
               '--insn', self.insn,
               '-o', str(self.logdir / f'stats_inputs.{self.experiment}.csv'),
               self.workdir, self.experiment]

        #TODO: This does not distinguish between --all runs?
        logfile = self.logdir / f'stats_inputs.log'
        run_and_log(cmd, logfile)

    def gather_timing_stats(self):
        self._begin(f"gather_timing_stats")
        cmd = [str(MYPATH / 'stats_timing.py'),
               '--insn', self.insn,
               '-o', str(self.logdir / f'stats_timing.{self.experiment}.csv'),
               '--os', str(self.logdir / f'stats_timing_summary.{self.experiment}.csv'),
               self.workdir, self.experiment]

        #TODO: This does not distinguish between --all runs?
        logfile = self.logdir / f'stats_timing.log'
        run_and_log(cmd, logfile)

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Orchestrate a run of experiments")
    p.add_argument("workdir", help="Working directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")
    p.add_argument("--all", help="Run on all mutants", action='store_true')
    p.add_argument("--no-parallel", help="Run everything serially", action='store_true')
    p.add_argument("--skip-mutants", help="Do not run mutation testing round #1", action='store_true')
    p.add_argument("--skip-eqvcheck", help="Do not run equivalence checking", action='store_true')
    p.add_argument("--skip-fuzzers", help="Do not run fuzzers", action='store_true')
    p.add_argument("--skip-round2", help="Do not run round 2 mutation testing", action='store_true')
    p.add_argument("--skip-stats", help="Do not update stats", action='store_true')
    p.add_argument("--timeout", help="Timeout to use (seconds)", type=int, default=90)

    args = p.parse_args()

    wp = WorkParams.load_from(args.workdir)
    logdir = Path(wp.workdir / f'expt.{args.experiment}')

    if not logdir.exists():
        logdir.mkdir()

    x = Orchestrator(args.workdir, args.experiment, args.insn, logdir, serial=args.no_parallel, timeout_s = args.timeout)

    # because we don't run as a package, we modify pythonpath to
    # allow deserialization.

    pythonpath = os.environ.get('PYTHONPATH', '')
    if len(pythonpath):
        pythonpath = str(MYPATH) + ':' + pythonpath
    else:
        pythonpath = str(MYPATH)

    os.environ['PYTHONPATH'] = pythonpath

    start = datetime.datetime.now()
    print("Started at", start)
    print(f"PYTHONPATH set to {os.environ['PYTHONPATH']}")

    if not args.skip_mutants: x.run_mutants()
    if not args.skip_eqvcheck: x.run_eqvcheck()

    if not args.skip_fuzzers:
        x.run_fuzzer('simple', run_all = args.all)
        x.run_fuzzer('custom', run_all = args.all)

    if not args.skip_eqvcheck: x.run_gather_witnesses()
    if not args.skip_fuzzers:
        x.run_collect_fuzzer('simple')
        x.run_collect_fuzzer('custom')

    if not args.skip_round2:
        # TODO: all?
        x.run_round2('eqvcheck')
        x.run_round2('fuzzer_simple')
        x.run_round2('fuzzer_custom')

    if not args.skip_stats:
        x.gather_mutant_stats()
        x.gather_survivor_stats()
        x.gather_input_stats()
        x.gather_timing_stats()

    end = datetime.datetime.now()
    print("End at", end)
    print("Total time", end - start) # should really be monotonic.
