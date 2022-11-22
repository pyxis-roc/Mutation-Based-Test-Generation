#!/usr/bin/env python3
#
# explain.py
# Explain the results for a particular mutant
#
#


import argparse
from rocprepcommon import *
from build_mutations import get_mutation_helper, get_mutators
from build_single_insn import Insn
import json

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

    # results of equivalence check?
    if mutant not in ir.not_equivalent:
        if mutant in ir.eqvcheck_timing:
            m['eqvcheck'] = "EQUIVALENT" if eqvresult['retcode'] == 0 else "UNKNOWN"
        else:
            m['eqvcheck'] = "UNKNOWN"
    else:
        m['eqvcheck'] = "NOT EQUIVALENT"

    print(m['eqvcheck'])

    # any warnings from compilation? # recompile with flags?

    # TODO: handle all_subset correctly
    m['survivors'] = {}
    for k in ['surv1', 'surv2.eqvcheck', 'surv2.fuzzer_simple', 'surv2.fuzzer_custom']:
        if ir.surv[k] is None:
            m['survivors'][k] = "NOT AVAILABLE"
        else:
            # KILLED in first round usually means never tested in other rounds unless --all is set.
            m['survivors'][k] = "SURVIVED" if mutant in ir.surv[k] else "KILLED"

    print(m['survivors'])

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
        if self.all_subset: raise NotImplementedError
        self.wp = wp
        self.mut = mut
        self.insn = insn
        self.expt = expt

        self.mutants = self.load_mutants()
        self.mutinfo = self.mut.get_mutation_information(insn)
        self.surv = get_survivors(self.wp, self.mut, self.insn, self.expt, self.all_subset)
        self.not_equivalent = self.load_non_equivalent()
        self.eqvcheck_timing = self.load_eqvcheck_timing()

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


if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Explain the results of a particular experiment")
    p.add_argument("workdir", help="Work directory")
    p.add_argument("--mutator", choices=get_mutators(), default="MUSIC")
    p.add_argument("--insn", help="Instruction to process (single instruction only!)")
    p.add_argument("experiment", help="Experiment")
    p.add_argument("mutant")

    args = p.parse_args()
    wp = WorkParams.load_from(args.workdir)
    mut = get_mutation_helper(args.mutator, wp)
    insn = Insn(args.insn)
    insn_results = InsnResults(wp, mut, insn, args.experiment, all_subset = False)

    explain_mutant(insn_results, args.mutant)
