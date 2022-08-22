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

class FuzzerExecutor:
    def __init__(self, wp, experiment):
        self.wp = wp
        self.experiment = experiment

    def run(self, insn, mutant):
        # this can make running repeats painful.
        odir = mutant.parent / f"fuzzer_output.{mutant.name}.{self.experiment}"

        cmd = [str(mutant), f"-exact_artifact_path={odir}"]

        print(" ".join(cmd))
        r = subprocess.run(cmd)
        print(r.returncode)
        #return r.returncode == 0

def run_fuzzer(wp, insn, experiment, muthelper, all_mutants = False):
    tt = InsnTest(wp, insn)

    workdir = wp.workdir / insn.working_dir

    mutants = muthelper.get_mutants(insn)
    survivors = muthelper.get_survivors(insn, experiment)

    executor = FuzzerExecutor(wp, experiment)

    with open(workdir / f"eqvcheck_results.{experiment}.json", "r") as f:
        not_equivalent = set(json.load(fp=f))

    if all_mutants:
        run_on = [x['target'] for x in mutants and x['src'] in not_equivalent]
    else:
        survivors = set(survivors)
        run_on = [x['target'] for x in mutants if x['src'] in survivors and x['src'] in not_equivalent]

    results = []
    for p in run_on:
        mutsrc = workdir / "libfuzzer_simple" / p
        res = executor.run(insn, mutsrc)
        if not res:
            results.append(p)

    with open(workdir / f"libfuzzer_simple_results.{experiment}.json", "w") as f:
        json.dump(results, fp=f)

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Run fuzzer on mutants")

    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("--mutator", choices=get_mutators(), default="MUSIC")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")
    p.add_argument("--all", help="Run the fuzzer on all mutants, not just survivors", action="store_true")

    args = p.parse_args()
    insns = get_instructions(args.insn)

    if len(insns):
        wp = WorkParams.load_from(args.workdir)
        muthelper = get_mutation_helper(args.mutator, wp)

        for i in insns:
            insn = Insn(i)
            run_fuzzer(wp, insn, args.experiment, muthelper, all_mutants = args.all)

