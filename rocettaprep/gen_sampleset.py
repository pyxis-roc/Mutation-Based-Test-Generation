#!/usr/bin/env python3

import argparse
import random
import difflib
import sys

SIM_THRESH = 0.8
MAT_THRESH = 0.7

def stratify(instructions):
    si = sorted(instructions)

    groups = []
    group = []
    for insn in si:
        if not len(insn): continue


        if len(group):
            prev = group[-1]
            sm = difflib.SequenceMatcher(None, prev, insn)
            m = sm.find_longest_match(0,len(prev),0,len(insn))
            matchsz = m.size / max(len(insn), len(prev))

            sim = sm.ratio()
            if sim < SIM_THRESH and not (matchsz > MAT_THRESH):
                groups.append(group)
                group = []
                print("****", file=sys.stderr)
            print(insn, prev, sim, matchsz, file=sys.stderr)

        group.append(insn)

    if len(group):
        groups.append(group)

    return groups

def sample(strata, sampleratio):
    out = []
    for s in strata:
        k = int(len(s) * sampleratio)
        if k < 1: k = 1
        out.extend(random.sample(s, k))

    return out

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate a stratified sample of the list of instructions, for use in --all instructions")
    p.add_argument("insnlist", help="Instruction list file")
    p.add_argument("nsampleratio", nargs="?", type=float, help="Sample ratio", default=0.33)
    p.add_argument("-s", dest="seed", type=int, help="Seed to initialize the random seed generator", default=202301021153)

    args = p.parse_args()

    random.seed(args.seed)

    with open(args.insnlist, "r") as f:
        insnlist = [x.strip() for x in f.readlines() if not x.startswith('#')]
        strata = stratify(insnlist)
        sample = sample(strata, args.nsampleratio)

    for s in sample:
        print(s)
