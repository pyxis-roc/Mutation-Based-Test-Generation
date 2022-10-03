#!/bin/bash

if [ $# -lt 2 ]; then
    echo Usage: $0 workdir expt
    exit 1;
fi;

P=$1/expt.$2/stats_survivors.$2.txt

echo -n "Identical kills: "; awk '/OK/ {print $2}' $P | sort | uniq | wc -l

