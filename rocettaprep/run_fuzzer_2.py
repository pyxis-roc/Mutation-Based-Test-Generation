#!/usr/bin/env python3
#
# run_fuzzer_2.py
#
# Run fuzzers.

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

from parsl.app.app import python_app, join_app
import parsl

@python_app
def run_fuzzer_on_mutant(executor, insn, mutsrc):
    return executor.run(insn, mutsrc)

@python_app
def finish_fuzzer(workdir, fuzzer, all_suffix, experiment, programs=[], inputs=[]):
    import json

    out = list(zip(programs, inputs))

    results = []
    for p, r in out:
        if not (r is None):
            results.append((p, r))

    # fuzzer doesn't have 'results' like eqvcheck?
    with open(workdir / f"libfuzzer_{fuzzer}_results{all_suffix}.{experiment}.json", "w") as f:
        json.dump(dict(results), fp=f)

@join_app
def run_fuzzer(wp, insn, experiment, muthelper, all_mutants = False, fuzzer = 'simple', parallel = True, timeout_s = 90, ignore_eqvcheck = False):
    import json
    from roctest import InsnTest
    from fuzzer_executor import FuzzerExecutor

    tt = InsnTest(wp, insn)

    workdir = wp.workdir / insn.working_dir

    mutants = muthelper.get_mutants(insn)

    executor = FuzzerExecutor(wp, experiment, 'all' if all_mutants else '', timeout_s = timeout_s)

    if all_mutants:
        all_suffix = '.all'
    else:
        all_suffix = ''

    if not ignore_eqvcheck:
        # equivalence checker must be run before fuzzer.
        with open(workdir / f"eqvcheck_results{all_suffix}.{experiment}.json", "r") as f:
            not_equivalent = set(json.load(fp=f))
    else:
        # consider everything to be not_equivalent if we don't have data from equivalence checker
        not_equivalent = set([x['src'] for x in mutants])

    if all_mutants:
        # we still restrict this to non-equivalent mutants?
        run_on = [x['target'] for x in mutants if x['src'] in not_equivalent]
    else:
        survivors = set(muthelper.get_survivors(insn, experiment))
        run_on = [x['target'] for x in mutants if x['src'] in survivors and x['src'] in not_equivalent]

    out = []
    programs = []
    for p in run_on:
        mutsrc = workdir / f"libfuzzer_{fuzzer}" / p
        programs.append(p)

        if parallel:
            out.append(run_fuzzer_on_mutant(executor, insn, mutsrc))
        else:
            out.append(executor.run(insn, mutsrc))

    return finish_fuzzer(workdir, fuzzer, all_suffix, experiment, programs, inputs=out)


if __name__ == "__main__":
    from setup_workdir import WorkParams
    from runconfig import config

    p = argparse.ArgumentParser(description="Run fuzzer on mutants")

    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("--mutator", choices=get_mutators(), default="MUSIC")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")
    p.add_argument("--all", help="Run the fuzzer on all non-equivalent mutants, not just survivors", action="store_true")
    p.add_argument("--ignore-eqvcheck", help="Ignore equivalence checker results, and run on all mutants (NOT RECOMMENDED)", action="store_true")

    p.add_argument("--fuzzer", help="Choose variant of fuzzer to run",
                   choices=['simple', 'custom'], default='simple')
    p.add_argument("--timeout", help="Timeout to use (seconds)",
                   type=int, default=90)

    args = p.parse_args()
    insns = get_instructions(args.insn)

    parsl.load(config)

    if len(insns):
        wp = WorkParams.load_from(args.workdir)
        muthelper = get_mutation_helper(args.mutator, wp)
        pt = PrepTimer()

        pt.start_timer()

        out = []
        for i in insns:
            insn = Insn(i)
            out.append(run_fuzzer(wp, insn, args.experiment, muthelper, all_mutants = args.all, fuzzer=args.fuzzer, parallel = True, timeout_s = args.timeout, ignore_eqvcheck = args.ignore_eqvcheck))

        for i, o in zip(insns, out):
            print(i)
            o.result()

        pt.end_timer()
