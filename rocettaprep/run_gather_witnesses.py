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
import inputgen

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

def bin_to_double(binary):
    return conform_c(float_hex2(struct.unpack('!d',struct.pack('!Q', int(binary, 2)))[0]))

def bin_to_int(b):
    return int(b, 2)

def bin_to_sint(b):
    v = int(b, 2)
    mx = 2**(len(b)-1)-1
    return v if v <= mx else v - 2**len(b)

CONVERTERS = {'float': bin_to_float,
              'double': bin_to_double,

              'signed int': bin_to_sint,
              'int8_t': bin_to_sint,
              'int16_t': bin_to_sint,
              'int64_t': bin_to_sint,

              'char': bin_to_sint, # TODO: verify
              'signed short int': bin_to_sint,
              'signed long int': bin_to_sint,

              'uint8_t': bin_to_int,
              'uint16_t': bin_to_int,
              'uint64_t': bin_to_int,
              'unsigned int': bin_to_int}

class CBMCOutput:
    def __init__(self, wp, experiment, subset = ''):
        self.wp = wp
        self.experiment = experiment
        self.subset = subset

    def _get_trace_variables(self, trace):
        assignments = []
        for e in trace:
            if e.get('stepType', None) == 'assignment' and e.get('assignmentType', None) == 'variable':
                var = e.get('lhs', '')
                if var.startswith('arg') or var.startswith('ret_'):
                    assignments.append(e)

        return assignments

    def _get_trace_variables_text(self, trace):
        assignments = []
        STATE = 0
        LINE = 1
        ASSIGN = 2
        curstate = -1

        for e in trace:
            if e.startswith('State'):
                state = STATE
            elif e.startswith('-'):
                state = LINE
            elif '=' in e and state == LINE:
                state = ASSIGN
                eq = e.index('=')
                var = e[:eq]
                value = e[eq+1:]
                if var.startswith('arg') or var.startswith('ret_'):
                    if not e.endswith('(assignment removed)'):
                        assignments.append({'lhs': var, 'value_text': value})

        return assignments

    def _parse_assignments_text(self, assignments):
        out = {}

        for a in assignments:
            var = a['lhs']
            if var not in out:
                out[var] = []

            v, b = a['value_text'].split(' ', 1)
            b = b[1:-1].replace(' ', '') # get rid of parens and spaces

            if v[-1] == "f":
                ty1 = 'float'
                ty2 = 'float'
            elif v[-1] == "u" or v[-2:] == "ul":
                ty1 = 'integer'
                if len(b) == 32:
                    ty2 = 'unsigned int' # pred
                else:
                    ty2 = f'uint{len(b)}_t'
            elif 'INFINITY' in v or 'NAN' in v:
                ty1 = 'float'
                ty2 = 'float'
            elif v[-1] in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9") or v[-1] == "l": #ul handled above
                ty1 = 'integer'
                if len(b) == 32:
                    ty2 = 'signed int'
                else:
                    ty2 = f'int{len(b)}_t'
            else:
                raise NotImplementedError(f"Unknown literal type: {v}")

            out[var].append({'name': ty1, 'type': ty2, 'binary': b, 'width': len(b)})

        return out

    def _fmt_value(self, d):
        ty = d['name']
        if ty == "integer":
            if d['type'] == '__CPROVER_size_t':
                ty = 'uint64_t'
            else:
                ty = d['type']
        elif ty == 'float':
            ty = 'float' if d['width'] == 32 else 'double' if d['width'] == 64 else None

        if ty in CONVERTERS:
            return str(CONVERTERS[ty](d['binary']))
        else:
            raise NotImplementedError(f"Don't know how to handle type {ty}")

    def gen_input_output_text(self, var_values):
        ninputs = len(var_values) - len([x for x in var_values if x.startswith('ret_')])

        inputs = []
        output = []
        for i in range(ninputs):
            inputs.append(self._fmt_value(var_values[f"arg{i}"][-1])) # always pick the last assignment

        if 'ret_orig' in var_values:
            output.append(self._fmt_value(var_values[f"ret_orig"][-1]))
        else:
            # multiple outputs
            noutputs = (len(var_values) - ninputs) // 2 # get rid of ret_mut
            assert noutputs > 1
            for i in range(noutputs):
                output.append(self._fmt_value(var_values[f"ret_orig.out{i}"][-1]))

        return inputs, output

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
                if d['type'] == '__CPROVER_size_t':
                    ty = 'uint64_t'
                else:
                    ty = d['type']
            elif ty == 'float':
                ty = 'float' if d['width'] == 32 else 'double' if d['width'] == 64 else None

            if ty in CONVERTERS:
                return str(CONVERTERS[ty](d['binary']))
            else:
                raise NotImplementedError(f"Don't know how to handle type {ty}")

        ninputs = len(var_values) - len([x for x in var_values if x.startswith('ret_')])

        inputs = []
        output = []
        for i in range(ninputs):
            inputs.append(fmt_value(var_values[f"arg{i}"][-1])) # always pick the last assignment

        # TODO: enable structure handling?
        output.append(fmt_value(var_values[f"ret_orig"][-1]))
        #output.append(fmt_value(var_values[f"ret_mut"][-1])) # TODO: log this?
        return inputs, output

    def get_inputs(self, insn, mutant, fmt = None):
        if self.subset == 'all':
            subset = '.all'
        else:
            subset = ''

        ofile_json = mutant.parent / f"cbmc_output.{mutant.name}{subset}.{self.experiment}.json"
        ofile_txt = mutant.parent / f"cbmc_output.{mutant.name}{subset}.{self.experiment}.txt"

        if ofile_json.exists() and ofile_txt.exists() and fmt is None:
            print(f"ERROR: {ofile_json} and {ofile_txt} both exist, use --trace-format to specify preference", file=sys.stderr)
            sys.exit(1)

        if fmt == 'json' or (fmt is None and ofile_json.exists()):
            return self.get_inputs_json(ofile_json)

        if fmt == 'text' or (fmt is None and ofile_txt.exists()):
            return self.get_inputs_text(ofile_txt)

    def get_inputs_json(self, ofile):
        with open(ofile, "r") as f:
            data = json.load(fp=f)

        status = data[-1]
        if "cProverStatus" in status:
            # TODO: avoid tracing unwinding assertions
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

    def get_inputs_text(self, ofile):
        with open(ofile, "r") as f:
            data = [x.strip() for x in f.readlines()]

        print(ofile)
        status = data[-1]
        if status == "VERIFICATION SUCCESSFUL":
            return None
        elif status == "VERIFICATION FAILED":
            line = 0
            for line, x in enumerate(data):
                if x.startswith('** Results:'):
                    break
            else:
                raise ValueError(f"{ofile}: status failed, but does not contain a result")

            line2 = 0
            trace_start = None
            for line2, re in enumerate(data[line:], line):
                if re.startswith("Trace for"):
                    if trace_start is None:
                        trace_start = line2
                    else:
                        # examine only the first trace by design
                        assignments = self._get_trace_variables_text(data[trace_start:line2])
                        break
            else:
                assert trace_start is not None, f"{ofile}: No trace found in result"
                # only trace in file
                assignments = self._get_trace_variables_text(data[trace_start:line2])

            var_values = self._parse_assignments_text(assignments)
            inp_out = self.gen_input_output_text(var_values)
            return tuple(inp_out[0]), inp_out[1]
        else:
            raise NotImplementedError(f"Status '{status}' not implemented")

def run_gather_witnesses(wp, insn, experiment, all_subset = False, trace_fmt = None):
    tt = InsnTest(wp, insn)

    workdir = wp.workdir / insn.working_dir

    if all_subset:
        subset = 'all.'
    else:
        subset = ''

    with open(workdir / f"eqvcheck_results.{subset}{experiment}.json", "r") as f:
        failed_mutants = json.load(fp=f)

    info = CBMCOutput(wp, experiment, 'all' if all_subset else '')

    outputs = {}
    duplicates = 0
    totalgen = 0

    for p in failed_mutants:
        mutsrc = workdir / "eqchk" / p
        inputs_out = info.get_inputs(insn, mutsrc, fmt = trace_fmt)
        print(f"eqvcheck: {p}: Got {inputs_out} from trace", file=sys.stderr)
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

    inputgen.write_inputgen(workdir / "eqchk",
                            subset, "eqvcheck", experiment, insn,
                            totalgen,
                            totalgen - duplicates)

    print(f"{insn.insn}: Equivalence checker generated {totalgen} witnesses with {totalgen-duplicates} unique inputs.", file=sys.stderr)

    inpfile = workdir / f"eqvcheck_inputs.{subset}{experiment}.ssv"
    outfile = workdir / "outputs" / f"eqvcheck_outputs.{subset}{experiment}.ssv"

    if len(outputs) > 0:
        with open(inpfile, "w") as fin:
            with open(outfile, "w") as fout:
                for x in outputs:
                    fin.write(" ".join(x)+"\n")
                    fout.write(" ".join(outputs[x])+"\n")

    inputgen.add_testcases(workdir, subset, 'eqvcheck', experiment, len(outputs), inpfile, outfile)

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Gather witness outputs from equivalence checkers")

    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")
    p.add_argument("--all", help="Process --all subset", action="store_true")
    p.add_argument("--trace-format", dest="trace_format", choices=['json', 'text'], help="Choose format of trace used by CBMC")

    args = p.parse_args()
    insns = get_instructions(args.insn)

    if len(insns):
        wp = WorkParams.load_from(args.workdir)

        for i in insns:
            insn = Insn(i)
            start = time.monotonic_ns()
            run_gather_witnesses(wp, insn, args.experiment, args.all, args.trace_format)
            end = time.monotonic_ns()
            print(f"{insn.insn}:{args.experiment}: gathering witnesses took {(end - start) / 1E6} ms", file=sys.stderr)
