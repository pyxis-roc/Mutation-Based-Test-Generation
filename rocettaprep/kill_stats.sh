#!/bin/bash

if [ $# -lt 2 ]; then
    echo Usage: $0 workdir expt
    exit 1;
fi;

P1=$1/expt.$2/stats_survivors.$2.txt
P2=$1/expt.$2/oracle_killed.txt

echo -n "Identical kills: "; awk '/OK/ {print $2}' $P1 | sort | uniq | wc -l
echo -n "Oracles killed: "; awk -F: '/killed/ {print $1}' $P2 | sort | wc -l

