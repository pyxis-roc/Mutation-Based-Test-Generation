#!/usr/bin/env python3

import argparse
import json
from rocprepcommon import *
from build_single_insn import Insn
from mutate import get_mutation_helper, get_mutators
import polars as pl

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Gather statistics on inputs generated")
    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("-o", "--output", help="Output file")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")

    args = p.parse_args()
    insns = get_instructions(args.insn)

    if len(insns):
        wp = WorkParams.load_from(args.workdir)

        out = []
        for i in insns:
            insn = Insn(i)

            for igsrc in ['eqchk', 'libfuzzer_simple', 'libfuzzer_custom']:
                f = wp.workdir / insn.working_dir / igsrc / f'inputgen.{args.experiment}.json'
                print(f)
                if f.exists():
                    print(f)
                    with open(f, "r") as fp:
                        d = json.load(fp=fp)
                        out.append(d)

        if len(out):
            df = pl.from_dicts(out)

            if args.output:
                df.write_csv(args.output)
            else:
                print(df)
    else:
        print(f"WARNING: No instructions specified, use --insn")
