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

from parsl.app.app import python_app
import parsl

# https://github.com/diffblue/cbmc/blob/48893287099cb5780302fe9dc415eb6888354fd6/src/util/exit_codes.h

CBMC_RC_OK = 0
CBMC_RC_PARSE_ERROR = 2
CBMC_RC_CONV_ERROR = 6
CBMC_RC_VERIFICATION_UNSAFE = 10 # also conversion error when writing to other file.

class CBMCExecutor:
    def __init__(self, wp, experiment):
        self.wp = wp
        self.experiment = experiment

    def run(self, insn, mutant):
        xinc = list(zip(itertools.repeat("-I"), self.wp.include_dirs))

        ofile = mutant.parent / f"cbmc_output.{mutant.name}.{self.experiment}.json"
        cmd = ["cbmc", "--json-ui", "--trace", "-I", str(self.wp.csemantics.parent)]
        cmd.extend(xinc)
        cmd.append(str(mutant))
        h = os.open(ofile, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode=0o666)
        print(" ".join(cmd))
        r = subprocess.run(cmd, stdout=h)
        os.close(h)
        return r.returncode

@python_app
def run_cbmc(cbmc, insn, mutsrc):
    return cbmc.run(insn, mutsrc)

def run_eqv_check(wp, insn, experiment, muthelper, all_mutants = False, parallel = True):
    tt = InsnTest(wp, insn)

    workdir = wp.workdir / insn.working_dir

    mutants = muthelper.get_mutants(insn)
    survivors = muthelper.get_survivors(insn, experiment)

    executor = CBMCExecutor(wp, experiment)

    if all_mutants:
        run_on = [x['src'] for x in mutants]
    else:
        run_on = survivors

    out = []
    for p in run_on:
        mutsrc = workdir / "eqchk" / p
        if parallel:
            out.append((p, run_cbmc(executor, insn, mutsrc)))
        else:
            out.append((p, executor.run(insn, mutsrc)))

    # TODO: distinguish conversion errors
    if parallel:
        #TODO: handle timeouts
        results = [x for x, y in out if y.result() == CBMC_RC_VERIFICATION_UNSAFE]
    else:
        results = [x for x, y in out if y == CBMC_RC_VERIFICATION_UNSAFE]

    if all_mutants:
        resfile = workdir / f"eqvcheck_results.all.{experiment}.json"
    else:
        resfile = workdir / f"eqvcheck_results.{experiment}.json"

    with open(resfile, "w") as f:
        json.dump(results, fp=f)

if __name__ == "__main__":
    from setup_workdir import WorkParams
    from parsl.configs.local_threads import config

    p = argparse.ArgumentParser(description="Run equivalence tests on mutants")

    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("--mutator", choices=get_mutators(), default="MUSIC")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")
    p.add_argument("--all", help="Run equivalence checks on all mutants, not just survivors", action="store_true")
    p.add_argument("--np", dest='no_parallel', help="Process serially", action="store_true")

    args = p.parse_args()
    insns = get_instructions(args.insn)

    parsl.load(config)

    if len(insns):
        wp = WorkParams.load_from(args.workdir)
        muthelper = get_mutation_helper(args.mutator, wp)

        for i in insns:
            insn = Insn(i)
            run_eqv_check(wp, insn, args.experiment, muthelper, all_mutants = args.all, parallel = not args.no_parallel)

