#!/bin/bash

set -e

P=`dirname $0`

if [ $# -lt 2 ]; then
    echo Usage: $0 workdir expt [--all]
    exit 1;
fi;

workdir=$1
expt=$2
all=$3
allp=""

if [ ! -z "$all" ]; then
    allp="all_"
fi;

$P/gen_pipeline.py -o ${allp}pipeline.$expt.csv $all $workdir $expt

$P/results_summary_pipeline.py ${allp}pipeline.$expt.csv -o ${allp}pipeline_stats_$expt.tex | tee ${allp}pipeline_other_$expt.txt

for src in eqvcheck fuzzer_simple fuzzer_custom; do
    echo "$P/gen_inputs.py -o ${allp}inputgen_${src}.${expt}.csv $all --src $src $workdir $expt"
    $P/gen_inputs.py -o ${allp}inputgen_${src}.${expt}.csv $all --src $src $workdir $expt
done;

$P/results_timing.py -o ${allp}input_timings_$expt.tex -og ${allp}inputgen_stats_$expt.tex ${allp}inputgen_eqvcheck.$expt.csv ${allp}inputgen_fuzzer_simple.$expt.csv ${allp}inputgen_fuzzer_custom.$expt.csv 
