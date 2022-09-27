#!/usr/bin/env python3
#
# run_eqvcheck.py
#
# Run and generate equivalence checker output.


import subprocess
import argparse
from roctest import *
from rocprepcommon import *
from build_single_insn import Insn
import json
import subprocess
from mutate import MUSICHelper, get_mutation_helper, get_mutators
import itertools
import os
import json
import sys

from parsl.app.app import python_app
import parsl

from runcommon import run_and_time

class FuzzerExecutor:
    def __init__(self, wp, experiment, subset = ''):
        self.wp = wp
        self.experiment = experiment
        self.subset = subset

    def make(self, mutant_exec):
        p = mutant_exec.parent
        t = mutant_exec.name

        print(f"{mutant_exec}: Compiling executable", file=sys.stderr)
        r, tm = run_and_time(["make", "-C", str(p), t])
        print(f"{mutant_exec}: Compilation took {tm/1E6} ms", file=sys.stderr)
        return r.returncode

    def run(self, insn, mutant):

        if self.subset:
            subset = 'all.'
        else:
            subset = ''

        # this can make running repeats painful.
        odir = mutant.parent / f"fuzzer_output.{mutant.name}.{subset}{self.experiment}"

        cmd = [str(mutant), f"-exact_artifact_path={odir}"]

        # run make always to ensure correct binaries
        r = self.make(mutant)
        if not (r == 0):
            print(f"{mutant}:ERROR: Compilation appears to have failed. Continuing anyway.",
                  file=sys.stderr)

        print(f"{mutant}: {' '.join(cmd)}", file=sys.stderr)

        try:
            r, t = run_and_time(cmd, timeout_s = 15)
            if t is not None:
                print(f"{mutant}:{subset}{self.experiment}: Total fuzzing time {t/1E6} ms, retcode = {r.returncode}", file=sys.stderr)
            else:
                print(f"{mutant}:{subset}{self.experiment}: Fuzzing timed out", file=sys.stderr)

            return {'time_ns': t, 'retcode': r.returncode}
        except FileNotFoundError:
            print(f"ERROR: {mutant} does not exist.", file=sys.stderr)
            return None

        assert False

@python_app
def run_fuzzer_on_mutant(executor, insn, mutsrc):
    return executor.run(insn, mutsrc)

def run_fuzzer(wp, insn, experiment, muthelper, all_mutants = False, fuzzer = 'simple', parallel = True):
    tt = InsnTest(wp, insn)

    workdir = wp.workdir / insn.working_dir

    mutants = muthelper.get_mutants(insn)
    survivors = muthelper.get_survivors(insn, experiment)

    executor = FuzzerExecutor(wp, experiment, 'all' if all_mutants else '')

    if all_mutants:
        all_suffix = '.all'
    else:
        all_suffix = ''

    # equivalence checker must be run before fuzzer.
    with open(workdir / f"eqvcheck_results{all_suffix}.{experiment}.json", "r") as f:
        not_equivalent = set(json.load(fp=f))

    if all_mutants:
        # we still restrict this to non-equivalent mutants?
        run_on = [x['target'] for x in mutants if x['src'] in not_equivalent]
    else:
        survivors = set(survivors)
        run_on = [x['target'] for x in mutants if x['src'] in survivors and x['src'] in not_equivalent]

    out = []
    for p in run_on:
        mutsrc = workdir / f"libfuzzer_{fuzzer}" / p

        if parallel:
            out.append((p, run_fuzzer_on_mutant(executor, insn, mutsrc)))
        else:
            out.append((p, executor.run(insn, mutsrc)))

    if parallel:
        out = [(p, r.result()) for p, r in out]

    results = []
    for p, r in out:
        if not (r is None):
            results.append((p, r))

    # fuzzer doesn't have 'results' like eqvcheck?
    with open(workdir / f"libfuzzer_{fuzzer}_results{all_suffix}.{experiment}.json", "w") as f:
        json.dump(dict(results), fp=f)

if __name__ == "__main__":
    from setup_workdir import WorkParams
    from runconfig import config

    p = argparse.ArgumentParser(description="Run fuzzer on mutants")

    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("--mutator", choices=get_mutators(), default="MUSIC")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")
    p.add_argument("--all", help="Run the fuzzer on all mutants, not just survivors (NOT RECOMMENDED)", action="store_true")
    p.add_argument("--fuzzer", help="Choose variant of fuzzer to run",
                   choices=['simple', 'custom'], default='simple')

    p.add_argument("--np", dest='no_parallel', help="Process serially", action="store_true")

    args = p.parse_args()
    insns = get_instructions(args.insn)

    parsl.load(config)

    if len(insns):
        wp = WorkParams.load_from(args.workdir)
        muthelper = get_mutation_helper(args.mutator, wp)

        for i in insns:
            insn = Insn(i)
            run_fuzzer(wp, insn, args.experiment, muthelper, all_mutants = args.all, fuzzer=args.fuzzer, parallel = not args.no_parallel)

