#!/usr/bin/env python3

import argparse
import polars as pl

def texify(table):
    out = []
    for r in table:
        out.append(" & ".join(r) + " \\\\")

    return "\n".join(out)

def gen_table(data, output):
    renames = {'kill1_ratio': 'Kill #1',
               'same_ratio': 'Same',
               'kill2_ratio_ec': 'Kill #2 (Eqv. Checker)',
               'kill2_ratio_fs': 'Kill #2 (Fuzzer/Simple)',
               'kill2_ratio_fc': 'Kill #2 (Fuzzer/Custom)',
               'left_ratio_ec': 'Left (Eqv. Checker)',
               'left_ratio_fs': 'Left (Fuzzer/Simple)',
               'left_ratio_fc': 'Left (Fuzzer/Custom)'}

    cols = data.columns
    print(cols)
    out = [["", "Min.", "Median", "Mean", "Std. Dev.", "Max."]]
    for r in data.rows():
        o = [renames[r[0]].replace('#', '\#')]
        o.extend([f"{x:0.2f}" for x in r[1:]])
        out.append(o)

    with open(output, "w") as f:
        print(texify(out), file=f)
        print(f"Written to {output}")
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Summarize data produced by gen_pipeline.py")

    p.add_argument("pipelinestatscsv", help="CSV produced by gen_pipeline.py")

    args = p.parse_args()

    stats = pl.read_csv(args.pipelinestatscsv)

    desc = stats['mutants'].describe()
    dd = dict(zip(desc['statistic'], desc['value']))

    # 689 + 255 disabled, all carry, lop3 variants [256], setp_q variants in all_insns_except_cc
    # all_insns_except_cc does not contain _cc_ variants; need to find that list.

    total_mutants = dd['count'] * dd['mean']
    print("Total instructions", dd['count'])
    print("Number of Mutants (Mean)", dd['mean'])
    print("Number of Mutants (Max)", dd['max'])
    print("Number of Mutants (Min)", dd['min'])
    print("Total Mutants", total_mutants)

    x = stats['Kill #1'].sum()
    print("Mutants killed overall", x, x / total_mutants)
    ratios = stats.with_columns([(pl.col('Kill #1') / pl.col('mutants') * 100).alias('kill1_ratio'),
                                 (pl.col('Same') / pl.col('mutants')  * 100).alias('same_ratio'),

                                 (pl.col('Kill.EC #2') / pl.col('mutants')  * 100).alias('kill2_ratio_ec'),
                                 (pl.col('Kill.FS #2') / pl.col('mutants')  * 100).alias('kill2_ratio_fs'),
                                 (pl.col('Kill.FC #2') / pl.col('mutants')  * 100).alias('kill2_ratio_fc'),

                                 (pl.col('Left.EC') / pl.col('mutants')  * 100).alias('left_ratio_ec'),
                                 (pl.col('Left.FS') / pl.col('mutants')  * 100).alias('left_ratio_fs'),
                                 (pl.col('Left.FC') / pl.col('mutants')  * 100).alias('left_ratio_fc'),
    ])

    x = ratios[['kill1_ratio', 'same_ratio',
                'kill2_ratio_ec', 'kill2_ratio_fs', 'kill2_ratio_fc',
                'left_ratio_ec', 'left_ratio_fs', 'left_ratio_fc']].describe()

    x = x[['kill1_ratio', 'same_ratio',
           'kill2_ratio_ec', 'kill2_ratio_fs', 'kill2_ratio_fc',
        'left_ratio_ec', 'left_ratio_fs', 'left_ratio_fc']].transpose(include_header=True, column_names=x['describe'])

    gen_table(x[['column', 'min', 'median', 'mean', 'std', 'max']], "pipeline_stats.tex")

    # Killed #1 + Same + Kill.EC #2 + Left.EC = Mutants
    ec_check = stats.with_columns([(pl.col('mutants') -
                                    (pl.col('Kill #1') + pl.col('Same') + pl.col('Kill.EC #2')
                                     + pl.col('Left.EC'))).alias('ec'),
                                   (pl.col('mutants') -
                                    (pl.col('Kill #1') + pl.col('Same') + pl.col('Kill.FS #2')
                                     + pl.col('Left.FS'))).alias('fs'),
                                   (pl.col('mutants') -
                                    (pl.col('Kill #1') + pl.col('Same') + pl.col('Kill.FC #2')
                                     + pl.col('Left.FC'))).alias('fc'),

    ])

    assert ec_check['ec'].sum() == 0
    assert ec_check['fs'].sum() == 0
    assert ec_check['fc'].sum() == 0

    # debug info
    print(ratios[['instruction', 'left_ratio_fs']].filter(pl.col('left_ratio_fs') >= 10))

    print(ratios[['instruction', 'same_ratio']].filter(pl.col('same_ratio') >= 10))
