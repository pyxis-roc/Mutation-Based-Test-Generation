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

from parsl.app.app import python_app, join_app
import parsl

import sys
import time

from cbmc_executor import *

@python_app
def run_cbmc(cbmc, insn, mutsrc):
    return cbmc.run(insn, mutsrc)

@python_app
def finish_eqv_check(workdir, all_mutants, experiment, programs = [], inputs = []):
    import json
    from run_eqvcheck_2 import CBMC_RC_VERIFICATION_UNSAFE

    out = list(zip(programs, inputs))
    results = [x for x, y in out if y['retcode'] == CBMC_RC_VERIFICATION_UNSAFE]

    if all_mutants:
        resfile = workdir / f"eqvcheck_results.all.{experiment}.json"
        timfile = workdir / f"eqvcheck_timing.all.{experiment}.json"
    else:
        resfile = workdir / f"eqvcheck_results.{experiment}.json"
        timfile = workdir / f"eqvcheck_timing.{experiment}.json"

    with open(resfile, "w") as f:
        json.dump(results, fp=f)

    with open(timfile, "w") as f:
        json.dump(dict(out), fp=f)

@join_app
def run_eqv_check(wp, insn, experiment, muthelper, all_mutants = False, parallel = True, timeout_s = 90):
    import json
    from roctest import InsnTest

    tt = InsnTest(wp, insn)

    workdir = wp.workdir / insn.working_dir

    mutants = muthelper.get_mutants(insn)
    survivors = muthelper.get_survivors(insn, experiment)

    executor = CBMCExecutor(wp, experiment, 'all' if all_mutants else '', timeout_s = timeout_s)

    if all_mutants:
        run_on = [x['src'] for x in mutants]
    else:
        run_on = survivors

    out = []
    programs = []

    for p in run_on:
        mutsrc = workdir / "eqchk" / p
        programs.append(p)
        if parallel:
            out.append(run_cbmc(executor, insn, mutsrc))
        else:
            out.append(executor.run(insn, mutsrc))

    return finish_eqv_check(workdir, all_mutants, experiment, programs, inputs=out)

if __name__ == "__main__":
    from setup_workdir import WorkParams
    from runconfig import htconfig

    p = argparse.ArgumentParser(description="Run equivalence tests on mutants")

    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("--mutator", choices=get_mutators(), default="MUSIC")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")
    p.add_argument("--all", help="Run equivalence checks on all mutants, not just survivors", action="store_true")
    p.add_argument("--timeout", help="Timeout to use (seconds)",
                   type=int, default=90)

    args = p.parse_args()
    insns = get_instructions(args.insn)

    parsl.load(htconfig)

    if len(insns):
        wp = WorkParams.load_from(args.workdir)
        muthelper = get_mutation_helper(args.mutator, wp)
        pt = PrepTimer()
        pt.start_timer()

        out = []
        for i in insns:
            insn = Insn(i)
            out.append(run_eqv_check(wp, insn, args.experiment, muthelper, all_mutants = args.all, parallel = True, timeout_s = args.timeout))

        for i, o in zip(insns, out):
            print(i)
            o.result()

        pt.end_timer()
