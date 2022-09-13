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
import time

# stolen from smt2utils
def conform_c(x):
    """Conform to C's %0.13a"""

    if x == "0x0.0p+0":
        return "0x0.0000000000000p+0"
    elif x == "-0x0.0p+0":
        return "-0x0.0000000000000p+0"
    else:
        return x

def float_hex2(x):
    """Replacement for float.hex that does not discards sign from NaN"""

    if math.isnan(x) and (math.copysign(1., x) == -1.0):
        return "-nan"

    return x.hex()

def bin_to_float(binary):
    return conform_c(float_hex2(struct.unpack('!f',struct.pack('!I', int(binary, 2)))[0]))

def bin_to_int(b):
    return int(b, 2)

def bin_to_sint(b):
    v = int(b, 2)
    mx = 2**(len(b)-1)-1

    return v if v < mx else v - 2**len(b)

CONVERTERS = {'float': bin_to_float,
              'signed int': bin_to_sint,
              'unsigned int': bin_to_int}

class CBMCOutput:
    def __init__(self, wp, experiment):
        self.wp = wp
        self.experiment = experiment

    def _get_trace_variables(self, trace):
        assignments = []
        for e in trace:
            if e.get('stepType', None) == 'assignment' and e.get('assignmentType', None) == 'variable':
                var = e.get('lhs', '')
                if var.startswith('arg') or var.startswith('ret_'):
                    assignments.append(e)

        return assignments

    def _parse_assignments(self, assignments):
        out = {}
        #print(assignments)
        for a in assignments:
            v = a['lhs']
            if v not in out:
                out[v] = []

            out[v].append(a['value'])

        return out

    def gen_input_output(self, var_values):
        def fmt_value(d):
            ty = d['name']
            if ty == "integer":
                ty = d['type']

            if ty in CONVERTERS:
                return str(CONVERTERS[ty](d['binary']))
            else:
                raise NotImplementedError(f"Don't know how to handle type {ty}")

        ninputs = len(var_values) - len([x for x in var_values if x.startswith('ret_')])

        inputs = []
        output = []
        for i in range(ninputs):
            inputs.append(fmt_value(var_values[f"arg{i}"][-1])) # always pick the last assignment

        output.append(fmt_value(var_values[f"ret_orig"][-1]))
        #output.append(fmt_value(var_values[f"ret_mut"][-1])) # TODO: log this?
        return inputs, output

    def get_inputs(self, insn, mutant):
        ofile = mutant.parent / f"cbmc_output.{mutant.name}.{self.experiment}.json"

        with open(ofile, "r") as f:
            data = json.load(fp=f)
        print(ofile)
        status = data[-1]
        if "cProverStatus" in status:
            if status["cProverStatus"] == "failure":
                for x in data:
                    if 'result' in x:
                        result = x['result']
                        break
                else:
                    raise ValueError(f"{ofile}: status failed, but does not contain a result")

                for re in result:
                    if "trace" in re:
                        # examine only the first trace by design
                        assignments = self._get_trace_variables(re["trace"])
                        break
                else:
                    assert False, f"{ofile}: No trace found in result"

                var_values = self._parse_assignments(assignments)
                inp_out = self.gen_input_output(var_values)
                return tuple(inp_out[0]), inp_out[1]
            elif status["cProverStatus"] == "success":
                return None
        else:
            if status.get('messageText', '') == 'CONVERSION ERROR':
                return None

            assert False, f"{ofile}:cProverStatus not found in status: {status}"

def run_gather_witnesses(wp, insn, experiment):
    tt = InsnTest(wp, insn)

    workdir = wp.workdir / insn.working_dir

    with open(workdir / f"eqvcheck_results.{experiment}.json", "r") as f:
        failed_mutants = json.load(fp=f)

    info = CBMCOutput(wp, experiment)

    outputs = {}
    duplicates = 0
    totalgen = 0

    for p in failed_mutants:
        mutsrc = workdir / "eqchk" / p
        inputs_out = info.get_inputs(insn, mutsrc)
        if inputs_out is None: continue
        inputs, out = inputs_out
        totalgen += 1
        if inputs in outputs:
             if not all([x1 == x2 for x1, x2 in zip(outputs[inputs], out)]):
                 # happens for sqrt, keep the first one
                 print(f"{insn.insn}: {p}: WARNING: Duplicate input {inputs} has multiple gold outputs: {outputs[inputs]} and {out}", file=sys.stderr)
             else:
                 # duplicate input/output
                 duplicates += 1
        else:
            outputs[inputs] = out

    with open(workdir / "eqchk" / f"inputgen.{experiment}.json", "w") as f:
        json.dump({'experiment': experiment,
                   'instruction': insn.insn,
                   'source': 'eqvcheck',
                   'total': totalgen,
                   'unique': totalgen - duplicates}, fp=f)

    print(f"{insn.insn}: Equivalence checker generated {totalgen} witnesses with {totalgen-duplicates} unique inputs.", file=sys.stderr)

    inpfile = workdir / f"eqvcheck_inputs.{experiment}.ssv"
    outfile = workdir / "outputs" / f"eqvcheck_outputs.{experiment}.ssv"

    with open(inpfile, "w") as fin:
        with open(outfile, "w") as fout:
            for x in outputs:
                fin.write(" ".join(x)+"\n")
                fout.write(" ".join(outputs[x])+"\n")

    with open(workdir / "testcases.json", "r") as f:
        testcases = json.load(fp=f)

    srcname = f'eqvcheck.{experiment}'

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

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Gather witness outputs from equivalence checkers")

    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")

    args = p.parse_args()
    insns = get_instructions(args.insn)

    if len(insns):
        wp = WorkParams.load_from(args.workdir)

        for i in insns:
            insn = Insn(i)
            start = time.monotonic_ns()
            run_gather_witnesses(wp, insn, args.experiment)
            end = time.monotonic_ns()
            print(f"{insn.insn}:{args.experiment}: gathering witnesses took {(end - start) / 1E6} ms", file=sys.stderr)
