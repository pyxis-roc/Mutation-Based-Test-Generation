#!/bin/bash

DST=insn-testgen-artifact

mkdir -p $DST
cp -a Mutation-Based-Test-Generation $DST
cp -a ROCetta-ptx-semantics $DST
mv $DST/Mutation-Based-Test-Generation/artifact_root/* $DST
rmdir $DST/Mutation-Based-Test-Generation/artifact_root
tar jcvf $DST.tar.bz2 $DST --remove-files
