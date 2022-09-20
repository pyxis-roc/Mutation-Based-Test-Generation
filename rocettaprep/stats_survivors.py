#!/usr/bin/env python3

import argparse
import json
from rocprepcommon import *
from build_single_insn import Insn
from mutate import get_mutation_helper, get_mutators
import polars as pl
import sys

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="")
    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("-o", "--output", help="Output file")
    p.add_argument("--mutator", choices=get_mutators(), default="MUSIC")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")

    args = p.parse_args()
    insns = get_instructions(args.insn)

    if args.output:
        output = open(args.output, "w")
    else:
        output = sys.stdout

    if len(insns):
        wp = WorkParams.load_from(args.workdir)
        muthelper = get_mutation_helper(args.mutator, wp)

        out = {}
        for i in insns:
            insn = Insn(i)

            #out[i] = {'experiment': args.experiment,
            #          'instruction': i}

            try:
                survivors = {}

                for r2source in ['eqvcheck', 'fuzzer_simple', 'fuzzer_custom']:
                    survivors[r2source] = set(muthelper.get_survivors(insn, args.experiment,
                                                                      round2=True, r2source=r2source))

            except FileNotFoundError as e:
                print(f"WARNING: {e}")
                pass


            okay = True
            sources = list(survivors.keys())
            for si, r2source in enumerate(sources):
                s = survivors[r2source]
                for sub in sources[si:]:
                    if sub == r2source: continue

                    if survivors[r2source] != survivors[sub]:
                        print(args.experiment, i, r2source, sub, survivors[r2source] - survivors[sub],
                              survivors[sub] - survivors[r2source], file=output)
                        okay = False

            if okay:
                print(args.experiment, i, "OK", file=output)
    else:
        print(f"WARNING: No instructions specified, use --insn")
