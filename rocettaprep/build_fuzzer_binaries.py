#!/usr/bin/env python3
#
# build_fuzzer_binaries.py
#
# Build fuzzer binaries before running the fuzzers.
#
# run_fuzzer will compile on demand, but mixing compilation and
# fuzzing appears to be have low throughput.
#
# This script will build all fuzzer binaries separately. Then
# run_fuzzer can be used to just run them.

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

from parsl.app.app import bash_app
import parsl
import os

from parsl.app.errors import BashExitFailure
from parsl.dataflow.error import DependencyError

@bash_app
def run_make(mutants, parallelism):
    p = set([m.parent for m in mutants])
    assert len(p) == 1, p

    t = set([m.name for m in mutants])

    cmd = f"make -C {p.pop()} {' '.join(t)} -j {parallelism}"

    return cmd

def run_build_fuzzer(wp, insn, experiment, muthelper, all_mutants = False, fuzzer = 'simple'):
    import json
    from roctest import InsnTest
    from fuzzer_executor import FuzzerExecutor
    import os
    import itertools

    parallelism = os.cpu_count()

    tt = InsnTest(wp, insn)

    workdir = wp.workdir / insn.working_dir

    mutants = muthelper.get_mutants(insn)

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
        survivors = set(muthelper.get_survivors(insn, experiment))
        run_on = [x['target'] for x in mutants if x['src'] in survivors and x['src'] in not_equivalent]


    out = []
    mutants = list([workdir / f"libfuzzer_{fuzzer}" / p for p in run_on])
    for i in range(0, len(mutants), parallelism):
        out.append(run_make(mutants[i:i+parallelism], parallelism))

    return out

def get_ba_result(header, ba):
    try:
        # for some reason, this does not catch parsl.app.error.BashAppNoReturn,
        # but it is logged to parsl.log.

        res = ba.result()
        if res == 0:
            print(f"{header}: Success.")
        return True
    except BashExitFailure as e:
        # exits with code 2 indicate compiler failures. With mutants, this is normal.
        print(f"{header}: Failed with code {e.exitcode}")
    except DependencyError as e:
        print(f"{header}: Workflow failed. Examine logs in runinfo (usually).")

    return False

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
            out.extend(run_build_fuzzer(wp, insn, args.experiment, muthelper, all_mutants = args.all, fuzzer=args.fuzzer))

        for i, o in zip(insns, out):
            get_ba_result(f"{i}:{args.experiment}:{args.fuzzer}", o)

        pt.end_timer()
