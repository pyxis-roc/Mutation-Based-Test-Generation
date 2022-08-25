#!/usr/bin/env python3
#
# run_gather_witnesses.py
#
# Gather witnesses (i.e. inputs) from equivalence checker output

import subprocess
import argparse
from roctest import *
from rocprepcommon import *
from build_single_insn import Insn
import json
import subprocess
from mutate import MUSICHelper, get_mutation_helper, get_mutators
import itertools
import os
import json
import math
import struct
import sys
from run_gather_witnesses import float_hex2
from roctest import InsnTest, TempFile

class FuzzerOutput:
    def __init__(self, wp, experiment):
        self.wp = wp
        self.experiment = experiment

    def gen_inputs(self, data, struct_fmt):
        def fmt_value(d, ty):
            if ty == "I":
                return str(d)
            elif ty == 'f':
                return float_hex2(d)
            elif ty == 'd':
                return float_hex2(d)
            elif ty == 'i':
                return str(d)
            else:
                raise NotImplementedError(f"Unhandled struct fmt type {ty}")

        inputs = []
        for i in range(len(data)):
            inputs.append(fmt_value(data[i], struct_fmt[i:i+1]))

        return inputs

    def get_inputs(self, insn, mutant):
        ofile = mutant.parent / f"fuzzer_output.{mutant.name}.{self.experiment}"

        if not ofile.exists():
            return None

        # could probably avoid reading this for every mutant...
        with open(ofile.parent / "struct_info.txt", "r") as f:
            struct_fmt = f.read()

        with open(ofile, "rb") as f:
            data = f.read()
            if len(data) == 0:
                print(f"WARNING: {ofile} is 0-byte, most likely the fuzzer crashed due to non-input reasons")
                return None

            unpacked_data = struct.unpack(struct_fmt, data)


            inp = self.gen_inputs(unpacked_data, struct_fmt)
            return tuple(inp)

def run_gather_fuzzer(wp, insn, experiment, muthelper, fuzzer = 'simple'):
    tt = InsnTest(wp, insn)

    workdir = wp.workdir / insn.working_dir

    mutants = muthelper.get_mutants(insn)
    info = FuzzerOutput(wp, experiment)

    output_inputs = set() # confusing .., used for deduplication
    for p in mutants:
        mutsrc = workdir / f"libfuzzer_{fuzzer}" / p['target']
        inputs = info.get_inputs(insn, mutsrc)
        if inputs is not None and inputs not in output_inputs:
            output_inputs.add(inputs)

    if len(output_inputs) == 0:
        return

    inpfile = workdir / f"libfuzzer_{fuzzer}_inputs.{experiment}.ssv"
    outfile = workdir / "outputs" / f"libfuzzer_{fuzzer}_outputs.{experiment}.ssv"

    with open(inpfile, "w") as fin:
        for x in output_inputs:
            fin.write(" ".join(x)+"\n")

    with open(workdir / "testcases.json", "r") as f:
        testcases = json.load(fp=f)

    srcname = f'libfuzzer_{fuzzer}.{experiment}'

    i = None
    for i, t in enumerate(testcases['tests']):
        if t['source'] == srcname:
            break # already there, will have the same parameters, so break
    else:
        testcases['tests'].append({'input': str(inpfile),
                                   'output': str(outfile),
                                   'source': srcname})

        with open(workdir / "testcases.json", "w") as f:
            json.dump(testcases, fp=f, indent='  ')

    it = InsnTest(wp, insn)
    it.set_insn_info(testcases)

    # always regenerate everything
    for t in it.gen_tests(filter_fn=lambda x: x[1]['source'] == f'libfuzzer_{fuzzer}.{experiment}',
                          output_fn = lambda ndx, tc, insn: TempFile(path=tc['output'])):
        cmdline = [c.get_name() if isinstance(c, TempFile) else c for c in t.cmdline]
        subprocess.run(cmdline, check=True)

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Gather fuzzer outputs (i.e. testcase inputs)")

    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")
    p.add_argument("--mutator", choices=get_mutators(), default="MUSIC")
    p.add_argument("--fuzzer", help="Choose variant of fuzzer outputs to collect",
                   choices=['simple', 'custom'], default='simple')

    args = p.parse_args()
    insns = get_instructions(args.insn)

    if len(insns):
        wp = WorkParams.load_from(args.workdir)
        muthelper = get_mutation_helper(args.mutator, wp)

        for i in insns:
            insn = Insn(i)
            run_gather_fuzzer(wp, insn, args.experiment, muthelper, fuzzer = args.fuzzer)

