#!/bin/bash

set -e

P=`dirname $0`

if [ $# -lt 2 ]; then
    echo Usage: $0 insnlist exptdir
    exit 1;
fi

$P/build_single_insn.py --insn "@$1" "$2"
$P/build_mutations.py --music `pwd`/MUSIC/music --insn "@$1" "$2"
$P/build_test_info.py --insn "@$1" "$2"
$P/build_eqvcheck_driver.py --insn "@$1" "$2"
$P/build_fuzzer_driver.py --insn "@$1" "$2"
$P/build_fuzzer_driver.py --insn "@$1" "$2" --fuzzer custom
$P/build_binaries.py --insn "@$1" "$2"
