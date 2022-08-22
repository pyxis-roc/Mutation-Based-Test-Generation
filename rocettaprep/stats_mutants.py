#!/usr/bin/env python3

import argparse
import json
from rocprepcommon import *
from build_single_insn import Insn
from mutate import get_mutation_helper, get_mutators

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="")
    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("--mutator", choices=get_mutators(), default="MUSIC")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")

    args = p.parse_args()
    insns = get_instructions(args.insn)

    if len(insns):
        wp = WorkParams.load_from(args.workdir)
        muthelper = get_mutation_helper(args.mutator, wp)

        out = {}
        for i in insns:
            insn = Insn(i)
            mutants = muthelper.get_mutants(insn)
            survivors = muthelper.get_survivors(insn, args.experiment)

            out[i] = {'survivors': len(survivors), 'mutants': len(mutants)}

            try:
                for r2source in ['eqvcheck', 'fuzzer_simple']:
                    survivors2 = muthelper.get_survivors(insn, args.experiment, round2=True, r2source=r2source)
                    out[i][f'round2.{r2source}'] = len(survivors2)
            except FileNotFoundError:
                pass

            eqvfile = wp.workdir / insn.working_dir / f'eqvcheck_results.{args.experiment}.json'
            if eqvfile.exists():
                with open(eqvfile, "r") as f:
                    noneq_mutants = json.load(fp=f)

            out[i][f'noneq_mutants'] = len(noneq_mutants)

        print(out)

