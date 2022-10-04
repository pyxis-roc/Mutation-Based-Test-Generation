#!/bin/bash

set -e

DST=insn-testgen-artifact

mkdir -p $DST
cd Mutation-Based-Test-Generation &&  git archive --prefix=Mutation-Based-Test-Generation/ HEAD | tar xf - -C ../$DST/
cd ..
cp -a ROCetta-ptx-semantics $DST
cp -a Data $DST

mv $DST/Mutation-Based-Test-Generation/artifact_root/* $DST
rmdir $DST/Mutation-Based-Test-Generation/artifact_root
tar jcvf $DST.tar.bz2 $DST --remove-files
