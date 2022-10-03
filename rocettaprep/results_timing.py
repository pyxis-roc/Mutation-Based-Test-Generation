#!/usr/bin/env python3

import argparse
import polars as pl
from results_summary_pipeline import texify

def gen_table(data, output, cols = ["series", "min", "mean", "std", "max", "count"],
              coltitles = ["", "Min.", "Median", "Mean", "Std. Dev.", "Max.", "Count"]):
    out = [coltitles]
    for r in data[cols].rows():
        o = [r[0]]
        o.extend([f"{x:0.2f}" for x in r[1:]])
        out.append(o)

    if output:
        with open(output, "w") as f:
            print(texify(out), file=f)
            print(f"Written to {output}")
    else:
        print(texify(out))

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Summarize data produced by gen_inputs.py")
    p.add_argument("eqvchkcsv", help="Equivalence checker input data")
    p.add_argument("fscsv", help="Fuzzer/Simple input data")
    p.add_argument("fccsv", help="Fuzzer/Custom input data")
    p.add_argument("-o", dest="output", help="Output file", default="input_timings.tex")
    p.add_argument("-og", dest="output_gen", help="Output file for input gen statistics", default="input_gen.tex")

    args = p.parse_args()

    eqvchk = pl.read_csv(args.eqvchkcsv)
    fs = pl.read_csv(args.fscsv)
    fc = pl.read_csv(args.fccsv)

    out = pl.DataFrame()
    names = []
    for t, n in [(eqvchk, 'Equivalence Checker'), (fs, 'Fuzzer/Simple'), (fc, 'Fuzzer/Custom')]:
        d = t['time_ms_avg'].describe()
        names.append(n)
        out = out.vstack(d[['value']].transpose(include_header=True, column_names=d['statistic']))

    out = out.hstack(pl.from_dict({'series': names}))
    gen_table(out, args.output)


    out = pl.DataFrame()

    for t, n in [(eqvchk, 'Equivalence Checker'), (fs, 'Fuzzer/Simple'), (fc, 'Fuzzer/Custom')]:
        d = t[['total', 'unique']].describe()
        dt = d[['total', 'unique']].transpose(include_header=True,
                                              column_names=d['describe'])
        dt = dt.with_column((n + " " + pl.col('column')).alias('series'))
        print(dt)
        out = out.vstack(dt)

    print(gen_table(out, args.output_gen, ["series", "min", "mean", "std", "max"],
                    ["", "Min.", "Median", "Mean", "Std. Dev.", "Max."]))


