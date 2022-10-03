#!/usr/bin/env python3

import argparse
import polars as pl
import ci
from pathlib import Path
if __name__ == "__main__":
    #from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Generate Pipeline statistics")

    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("-o", "--output", help="Output file")

    args = p.parse_args()

    #wp = WorkParams.load_from(args.workdir)

    wp = Path(args.workdir)

    expt_dir = wp / f'expt.{args.experiment}'

    if not expt_dir.exists():
        print(f"ERROR: {expt_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    stats_file = expt_dir / f'stats_mutants.{args.experiment}.csv'
    if not stats_file.exists():
        print(f"ERROR: {stats_file} does not exist, make sure you've run stats_mutants.py",
              file=sys.stderr)

        sys.exit(1)

    stats_file = expt_dir / f'stats_mutants.{args.experiment}.csv'
    if not stats_file.exists():
        print(f"ERROR: {stats_file} does not exist, make sure you've run stats_mutants.py",
              file=sys.stderr)

        sys.exit(1)


    timing_file = expt_dir / f'stats_timing_summary.{args.experiment}.csv'
    if not timing_file.exists():
        print(f"ERROR: {timing_file} does not exist, make sure you've run stats_timing.py",
              file=sys.stderr)

        sys.exit(1)

    stats = pl.read_csv(stats_file)
    timing = pl.read_csv(timing_file)

    mutant_timing = timing.filter(pl.col("source") == "mutation")
    stats = stats.join(mutant_timing, on=["experiment", "instruction"])

    stats = stats.with_columns([
        pl.col('time_ns_count').apply(lambda c: ci.critlevel(c, 95)).alias("_time_ns_critlevel"),
    ])

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
            (pl.col('time_ns_avg') / 1E6).alias("time_ms_avg"),
            pl.struct(["time_ns_count", "time_ns_stdev", "_time_ns_critlevel"]).apply(lambda x: ci.calc_ci_2(x['_time_ns_critlevel'], x['time_ns_stdev'] / 1E6, x['time_ns_count'])).alias("time_ms_ci95")
        ])

    # for now, print out individual kills, but in final version
    # unless kills differ, remove individual kill columns.

    pipeline_stats = stats[["instruction", "mutants", "Kill #1", "Same", 'Kill.EC #2', 'Kill.FS #2', 'Kill.FC #2', 'Left.EC', 'Left.FS', 'Left.FC', 'time_ms_avg', 'time_ms_ci95']]

    if args.output:
        pipeline_stats.write_csv(args.output)
    else:
        print(pipeline_stats)


