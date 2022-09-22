#!/usr/bin/env python

import argparse
import json
from rocprepcommon import *
from build_single_insn import Insn
from mutate import get_mutation_helper, get_mutators
import polars as pl

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Extract timing statistics from log files")
    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("-o", "--output", help="Output file for raw data")
    p.add_argument("--os", help="Output file for summary data")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")

    args = p.parse_args()
    insns = get_instructions(args.insn)

    if len(insns):
        wp = WorkParams.load_from(args.workdir)

        out = []
        for i in insns:
            insn = Insn(i)

            # we seem to be ignoring round2 timing for re-running mutants?

            for timsrc, src in [(f'eqvcheck_timing.{args.experiment}.json', 'eqvcheck'),
                                (f'libfuzzer_simple_results.{args.experiment}.json', 'fuzzer_simple'),
                                (f'libfuzzer_custom_results.{args.experiment}.json', 'fuzzer_custom'),
                                (f'mutant_timing.{args.experiment}.json', 'mutation'),

                                (f'eqvcheck_timing.all.{args.experiment}.json', 'all.eqvcheck'),
                                (f'libfuzzer_simple_results.all.{args.experiment}.json', 'all.fuzzer_simple'),
                                (f'libfuzzer_custom_results.all.{args.experiment}.json', 'all.fuzzer_custom'),
            ]:

                f = wp.workdir / insn.working_dir / timsrc
                if f.exists():
                    print(f)
                    with open(f, "r") as fp:
                        d = json.load(fp=fp)

                        for k, v in d.items():
                            vv = {'experiment': args.experiment,
                                  'source': src,
                                  'instruction': insn.insn,
                                  'mutant': k,
                                  'time_ns': v['time_ns'] if 'time_ns' in v else None,
                                  }
                            out.append(vv)

        if len(out):
            df = pl.from_dicts(out)

            if args.output:
                df.write_csv(args.output)
            else:
                print(df)

            summ = df.groupby(['experiment', 'source', 'instruction']).agg([pl.sum('time_ns').alias("time_ns_sum"),
                                                                            pl.mean('time_ns').alias("time_ns_avg"),
                                                                            pl.col('time_ns').len().alias("time_ns_count"),
                                                                            pl.std('time_ns').alias("time_ns_stdev")
                                                                            ])
            if args.os:
                summ.write_csv(args.os)
            else:
                print(summ)
    else:
        print(f"WARNING: No instructions specified, use --insn")
