#!/bin/bash

set -e

DST=insn-testgen-artifact

mkdir -p $DST
cp -a Mutation-Based-Test-Generation $DST
cp -a ROCetta-ptx-semantics $DST
cp -a Data $DST

mv $DST/Mutation-Based-Test-Generation/artifact_root/* $DST
rmdir $DST/Mutation-Based-Test-Generation/artifact_root
tar jcvf $DST.tar.bz2 $DST --remove-files
