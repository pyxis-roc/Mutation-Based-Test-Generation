#!/usr/bin/env python3

import argparse
import polars as pl
import ci

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Generate Table 3, equivalence checker stats")

    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("-o", "--output", help="Output file")
    p.add_argument("--all", help="Process --all data", action="store_true") # this generates table 4
    p.add_argument("--src", help="Source", choices=['eqvcheck', 'fuzzer_simple', 'fuzzer_custom'],
                   default='eqvcheck')

    args = p.parse_args()

    wp = WorkParams.load_from(args.workdir)

    expt_dir = wp.workdir / f'expt.{args.experiment}'

    if not expt_dir.exists():
        print(f"ERROR: {expt_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    stats_file = expt_dir / f'stats_inputs.{args.experiment}.csv'
    if not stats_file.exists():
        print(f"ERROR: {stats_file} does not exist, make sure you've run stats_inputs.py",
              file=sys.stderr)

        sys.exit(1)

    timing_file = expt_dir / f'stats_timing_summary.{args.experiment}.csv'
    if not timing_file.exists():
        print(f"ERROR: {timing_file} does not exist, make sure you've run stats_timing.py",
              file=sys.stderr)

        sys.exit(1)

    if args.src.startswith('fuzzer'):
        inpsrc = 'lib' + args.src
    else:
        inpsrc = args.src

    if args.all:
        src = f'all.{args.src}'
        inpsrc = f'all.{inpsrc}'
    else:
        src = args.src

    stats = pl.read_csv(stats_file).filter(pl.col("source") == inpsrc)
    timing = pl.read_csv(timing_file)

    eqvcheck_timing = timing.filter(pl.col("source") == src)
    stats = stats.join(eqvcheck_timing, on=["experiment", "instruction"])

    stats = stats.with_columns([
        pl.col('time_ns_count').apply(lambda c: ci.critlevel(c, 95)).alias("_time_ns_critlevel"),
    ])

    stats = stats.with_columns(
        [
            (pl.col('time_ns_avg') / 1E6).alias("time_ms_avg"),
            pl.struct(["time_ns_count", "time_ns_stdev", "_time_ns_critlevel"]).apply(lambda x: ci.calc_ci_2(x['_time_ns_critlevel'], x['time_ns_stdev'] / 1E6, x['time_ns_count'])).alias("time_ms_ci95")
        ])

    tbl = stats[["instruction", 'total', 'unique', 'time_ms_avg', 'time_ms_ci95']]

    if args.output:
        tbl.write_csv(args.output)
    else:
        print(tbl)
