#!/bin/bash

DSUFFIX=`date +%Y%m%d%H%M`
TOT=${1:-5}
INPUT=${2:-../../list}

for((r=1;r<=$TOT;r++)); do
    suff=$DSUFFIX-$r
    python L2_runner.py /localdisk2/sree/mutation/MUSIC/music /localdisk2/sree/mutation/pycparser-release_v2.20/utils/fake_libc_include/ no-yaml  $INPUT $RUNNER_ARGS 2>&1 | tee run-${suff}.txt

    mkdir run-${suff}

    mv mutated-programs-* working-directory-* new_inputs_* output*.json run-${suff}.txt run-${suff}/
done;

