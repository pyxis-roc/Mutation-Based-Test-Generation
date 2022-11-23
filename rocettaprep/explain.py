#!/usr/bin/env python3
#
# explain.py
# Explain the results for a particular mutant
#
#


import argparse
from rocprepcommon import *
from build_mutations import get_mutation_helper, get_mutators
from build_single_insn import Insn, PTXSemantics
import json
import subprocess
import re
import gzip
import sys

def get_compile_output(insn_result, mutant):
    if mutant in insn_result.compiler_output:
        return None, "".join(insn_result.compiler_output[mutant])
    else:
        if insn_result.mutants_compiled == len(insn_result.mutants):
            # usually indicates no interesting output
            return None, ""
        else:
            print(f"WARNING: {mutant} compiler output not found, so recompiling", file=sys.stderr)
            # usually the make output is incomplete, so for now, recompile
            mutant = insn_result.mutants[mutant]['src']
            target = "/tmp/test.o"

            # note missing "../" +insn_result.insn.test_file
            cmds = insn_result.ps.get_compile_command_primitive(mutant, "../" +insn_result.insn.test_file, target, cflags=["-g", "-O3", "-Wuninitialized"])
            assert len(cmds) == 1

            try:
                output = subprocess.check_output(cmds[0], cwd=insn_result.wp.workdir / insn_result.insn.working_dir / insn_result.mut.srcdir, stderr=subprocess.STDOUT)
                return True, output.decode('utf-8')
            except subprocess.CalledProcessError as e:
                return False, e.output.decode('utf-8')

def _get_lines(filename, start, end):
    with open(filename, "r") as f:
        out = []
        for line, c in enumerate(f.readlines(), 1):
            if line >= start and line <= end:
                out.append(c)

            if line > end: break

        return out

def annotate(lines, coord, line_offset = 0):
    cur_line = line_offset

    out = []
    for i in range(coord.start_line, coord.end_line+1):
        line = lines[i - line_offset]
        out.append(line)

        anno_start_col = coord.start_col if i == coord.start_line else 0
        anno_end_col = coord.end_col if i == coord.end_line else len(line)
        out.append(" "*(anno_start_col-1) + "^" * (anno_end_col - anno_start_col) + "\n")

    x = lines[:(coord.start_line-line_offset)]
    x.extend(out)
    x.extend(lines[coord.end_line-line_offset+1:])

    return x

def get_mutation(wp, mut, insn, mutant, mutinfo):
    srcfile = wp.workdir / insn.working_dir / insn.sem_file
    mutantfile = wp.workdir / insn.working_dir / mut.srcdir / mutant

    srccoord = mut.get_source_coord(mutinfo[mutant])
    mutcoord = mut.get_source_coord(mutinfo[mutant], before=False)

    orig = "".join(annotate(_get_lines(srcfile, srccoord.start_line, srccoord.end_line),
                            srccoord, line_offset=srccoord.start_line))

    mutated = "".join(annotate(_get_lines(mutantfile, mutcoord.start_line, mutcoord.end_line),
                               mutcoord, line_offset=mutcoord.start_line))

    return {'original': orig, 'mutated': mutated}

def analyze_mutant_rounds(insn_result, mutant):
    ir = insn_result
    mutant = ir.mutants[mutant]['src']
    target = ir.mutants[mutant]['target']

    out = {}
    mut_timings = ir.mutant_timing
    surv = ir.surv

    keys = [('surv1', 'mut1')]
    keys.extend([(f'surv2.{f}', f'mut2.{f}') for f in ('eqvcheck', 'fuzzer_simple', 'fuzzer_custom')])

    for sk, mtk in keys:
        if mtk in mut_timings and mut_timings[mtk] is not None:
            if sk in surv and surv[sk] is not None:
                if target in mut_timings[mtk]:
                    # mutant was run
                    if mutant in surv[sk]:
                        out[sk] = "SURVIVED"
                    else:
                        out[sk] = "KILLED"
                else:
                    assert mutant not in surv[sk], f"{mutant} was not run, but in survivors"
                    out[sk] = "NOT RUN"
            else:
                out[sk] = "FAIL:MUTANT-TIMING-ONLY/NO-SURVIVOR-INFO"
        else:
            if sk in surv and surv[sk] is not None:
                out[sk] = "FAIL:NO-MUTANT-TIMING-INFO/SURVIVOR-ONLY"
            else:
                out[sk] = "NOT AVAILABLE"

    return out

def analyze_eqvcheck(insn_result, mutant):
    ir = insn_result

    if mutant in ir.eqvcheck_timing:
        if mutant in ir.not_equivalent:
            return "NOT EQUIVALENT"
        else:
            return "EQUIVALENT" if ir.eqvcheck_timing[mutant]['retcode'] == 0 else "UNKNOWN"
    else:
        # missing eqvcheck_timing means it was never checked
        # usually because it was killed in first round
        return "NOT CHECKED"

def analyze_compiler(compiler_output, mutant):
    warnings_re = re.compile(f"^{mutant}:\\d+:\\d+: warning: .*$", re.MULTILINE)

    out = set()
    for w in re.finditer(warnings_re, compiler_output):
        m = w.group(0)
        if "[-Wuninitialized]" in m:
            out.add("warning-uninitialized")
        else:
            out.add("warning-unknown")

    return out

def explain_mutant(insn_result, mutant):
    ir = insn_result
    mutant = ir.mutants[mutant]['src']
    target = ir.mutants[mutant]['target']

    m = get_mutation(ir.wp,
                     ir.mut,
                     ir.insn, mutant,
                     ir.mutinfo)
    print(m['original'])
    print(m['mutated'])

    binary = ir.wp.workdir / ir.insn.working_dir / ir.mut.srcdir / target

    if not binary.exists():
        print(f'{binary} does not exist')
    else:
        print(f'{binary} exists')
        # any warnings from compilation? # recompile with flags?

    compile_ok, output = get_compile_output(ir, mutant)
    m['compile_ok'] = compile_ok
    m['compiler_output'] = output
    m['compiler_analysis'] = []

    if not compile_ok:
        m['compiler_analysis'] = list(analyze_compiler(output, mutant))

    print(m['compiler_analysis'])

    m['eqvcheck'] = analyze_eqvcheck(insn_result, mutant)
    print(m['eqvcheck'])

    m['survivors'] = analyze_mutant_rounds(insn_result, mutant)
    print(m['survivors'])
    # TODO: handle all_subset correctly

def get_survivors(wp, mut, insn, experiment, all_subset = False):
    # load all survivors if possible
    out = {'surv1': None,
           'surv2.eqvcheck': None,
           'surv2.fuzzer_simple': None,
           'surv2.fuzzer_custom': None}

    try:
        out['surv1'] = set(mut.get_survivors(insn, args.experiment, all_subset = all_subset))
    except FileNotFoundError:
        pass

    for r2source in ['eqvcheck', 'fuzzer_simple', 'fuzzer_custom']:
        try:
            out[f'surv2.{r2source}'] = set(mut.get_survivors(insn, args.experiment, round2 = True,
                                                             r2source=r2source, all_subset = all_subset))
        except FileNotFoundError:
            pass

    return out

class InsnResults:
    def __init__(self, wp, mut, insn, expt, all_subset = False):
        self.all_subset = all_subset
        self.wp = wp
        self.mut = mut
        self.insn = insn
        self.expt = expt

        self.ps = PTXSemantics(wp.csemantics, []) # only for compiling
        self.mutants = self.load_mutants()
        self.mutinfo = self.mut.get_mutation_information(insn)
        self.surv = get_survivors(self.wp, self.mut, self.insn, self.expt, self.all_subset)
        self.not_equivalent = self.load_non_equivalent()
        self.eqvcheck_timing = self.load_eqvcheck_timing()
        self.mutant_timing = self.load_mutant_timing()
        self.compiler_output = self.load_compiler_output()

    def load_mutants(self):
        return dict([(x['src'], x) for x in self.mut.get_mutants(self.insn)])

    def load_non_equivalent(self):
        all_suffix = ".all" if self.all_subset else ""

        with open(self.wp.workdir / self.insn.working_dir / f"eqvcheck_results{all_suffix}.{self.expt}.json", "r") as f:
            not_equivalent = set(json.load(fp=f))

        return not_equivalent

    def load_eqvcheck_timing(self):
        all_suffix = ".all" if self.all_subset else ""

        with open(self.wp.workdir / self.insn.working_dir / f"eqvcheck_timing{all_suffix}.{self.expt}.json", "r") as f:
            timing = json.load(fp=f)

        return timing

    def load_compiler_output(self): # for mutants
        mof = self.wp.workdir / self.insn.working_dir / self.mut.srcdir / "make.output.gz"
        out = {}
        ire = re.compile(r"^(.*\.c):\d+:\d+: (error|warning).*$")
        targets = 0
        if mof.exists():
            with gzip.open(mof, "r") as f:
                for l in f:
                    ls = l.decode('utf-8')
                    if ls.startswith('make: Entering directory'):
                        targets += 1

                    m = ire.match(ls)
                    if m:
                        src = m.group(1)
                        if src not in out: out[src] = []
                        out[src].append(m.group(0))

        self.mutants_compiled = targets
        return out

    def load_mutant_timing(self):
        out = {'mut1': None,
               'mut2.eqvcheck': None,
               'mut2.fuzzer_simple': None,
               'mut22.fuzzer_custom': None}

        try:
            out['mut1'] = set(self.mut.get_test_timings(self.insn, self.expt,
                                                        all_subset = self.all_subset))
        except FileNotFoundError:
            pass

        for r2source in ['eqvcheck', 'fuzzer_simple', 'fuzzer_custom']:
            try:
                out[f'mut2.{r2source}'] = set(self.mut.get_test_timings(self.insn, self.expt,
                                                                        round2 = True, r2source=r2source, all_subset = self.all_subset))
            except FileNotFoundError:
                pass

        return out


if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Explain the results of a particular experiment")
    p.add_argument("workdir", help="Work directory")
    p.add_argument("--mutator", choices=get_mutators(), default="MUSIC")
    p.add_argument("--insn", help="Instruction to process (single instruction only!)")
    p.add_argument("--all", help="Use the all subset data", action="store_true")
    p.add_argument("experiment", help="Experiment")
    p.add_argument("mutant", help="Mutant source file, or @all for all")

    args = p.parse_args()
    wp = WorkParams.load_from(args.workdir)
    mut = get_mutation_helper(args.mutator, wp)
    insn = Insn(args.insn)
    insn_results = InsnResults(wp, mut, insn, args.experiment, all_subset = args.all)

    if args.mutant == '@all':
        mutants = insn_results.mutants
    else:
        mutants = [args.mutant]

    for m in mutants:
        print(f"===> {m} <===")
        explain_mutant(insn_results, m)
        print("")
