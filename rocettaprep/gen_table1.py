#!/usr/bin/env python3

import argparse
import polars as pl

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Generate Table 1")

    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("-o", "--output", help="Output file")

    args = p.parse_args()

    wp = WorkParams.load_from(args.workdir)

    expt_dir = wp.workdir / f'expt.{args.experiment}'

    if not expt_dir.exists():
        print(f"ERROR: {expt_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    stats_file = expt_dir / f'stats_mutants.{args.experiment}.csv'

    if not stats_file.exists():
        print(f"ERROR: {stats_file} does not exist, make sure you've run stats_mutants.py",
              file=sys.stderr)

        sys.exit(1)

    stats = pl.read_csv(stats_file)

    stats = stats.with_columns(
        [
            (pl.col('mutants') - pl.col('survivors')).alias("Kill #1"),
            (pl.col('survivors') - pl.col('noneq_mutants')).alias("Same"),
            (pl.col('noneq_mutants') - pl.col('round2.eqvcheck')).alias("Kill.EC #2"),
            (pl.col('noneq_mutants') - pl.col('round2.fuzzer_simple')).alias("Kill.FS #2"),
            (pl.col('noneq_mutants') - pl.col('round2.fuzzer_custom')).alias("Kill.FC #2"),
            (pl.col('round2.eqvcheck')).alias("Left.EC"),
            (pl.col('round2.fuzzer_simple')).alias("Left.FS"),
            (pl.col('round2.fuzzer_custom')).alias("Left.FC"),
        ])

    print(stats[["instruction", "mutants", "Kill #1", "Same", 'Kill.EC #2', 'Kill.FS #2', 'Kill.FC #2', 'Left.EC', 'Left.FS', 'Left.FC']])

