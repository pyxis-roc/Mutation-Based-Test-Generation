#!/usr/bin/env python3
#
# run_mutants.py
#
# Run and generate mutant output, akin to the "kill mutants" step.


import subprocess
import argparse
from roctest import *
from rocprepcommon import *
from build_single_insn import Insn
import json
import subprocess
from mutate import MUSICHelper, get_mutation_helper, get_mutators

from mutate import get_mutation_helper, get_mutators
from parsl.app.app import python_app
import parsl

def run_single_test(wp, insn, test_info):
    def compare(wp, insn, test_info):
        output_file = test_info.tmp_output.get_name()
        gold_file = wp.workdir / insn.working_dir / "outputs" / test_info.gold_output.name

        r = subprocess.run(['diff', '-q', str(output_file), str(gold_file)])
        return r.returncode == 0

    cmdline = [x if not isinstance(x, TempFile) else x.get_name() for x in test_info.cmdline]

    try:
        r = subprocess.run(cmdline, check=True)
        return compare(wp, insn, test_info)
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        # missing binaries should be handled differently?
        return False

@python_app
def run_tests_on_mutant(wp, insn, mut, tt, muthelper, filter_fn):
    workdir = wp.workdir / insn.working_dir

    for test in tt.gen_tests(binary = workdir / muthelper.srcdir / mut['target'],
                             filter_fn = filter_fn):

        res = run_single_test(wp, insn, test)

        for x in test.cmdline:
            if isinstance(x, TempFile): x.cleanup()

        if not res: break
    else:
        # mutant survived tests
        return mut['src']

    # mutant was killed
    return None

def run_tests(wp, insn, muthelper, experiment, round2 = False, r2source = 'eqvcheck'):
    tt = InsnTest(wp, insn)
    tt.load_tests()

    workdir = wp.workdir / insn.working_dir
    mutants = muthelper.get_mutants(insn)

    if round2:
        with open(workdir / f"eqvcheck_results.{experiment}.json") as f:
            non_eq_mutants = set(json.load(fp=f))

        mutants = [x for x in mutants if x['src'] in non_eq_mutants]

        if r2source == 'eqvcheck':
            filter_fn = lambda x: x[1]['source'] == f'eqvcheck.{experiment}'
        elif r2source == 'fuzzer_simple':
            filter_fn = lambda x: x[1]['source'] == f'libfuzzer_simple.{experiment}'
        elif r2source == 'fuzzer_custom':
            filter_fn = lambda x: x[1]['source'] == f'libfuzzer_custom.{experiment}'
        else:
            raise NotImplementedError(f"Unrecognized r2source '{r2source}'")
    else:
        # don't use tests generated by translation validator (verifyce)
        # or by eqvcheck
        filter_fn = lambda x: x[1]['source'] == f'gen_tests'

    out = []
    for mut in mutants:
        res = run_tests_on_mutant(wp, insn, mut, tt, muthelper, filter_fn)
        out.append(res)

    out = list(filter(lambda x: x is not None, [x.result() for x in out]))
    return out

if __name__ == "__main__":
    from setup_workdir import WorkParams
    from parsl.configs.local_threads import config

    p = argparse.ArgumentParser(description="Run tests on mutants")

    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("--mutator", choices=get_mutators(), default="MUSIC")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")
    p.add_argument("--round2", help="Second round, so run only on survivors using tests generated by eqvcheck or the fuzzer", action='store_true')
    p.add_argument("--r2source", help="Source for second round tests", choices=['eqvcheck', 'fuzzer_simple', 'fuzzer_custom'], default='eqvcheck')

    args = p.parse_args()
    insns = get_instructions(args.insn)

    parsl.load(config)

    if len(insns):
        wp = WorkParams.load_from(args.workdir)
        muthelper = get_mutation_helper(args.mutator, wp)

        for i in insns:
            insn = Insn(i)
            survivors = run_tests(wp, insn, muthelper, args.experiment, args.round2, args.r2source)
            print(f"{len(survivors)} survivors for {i}")

            if args.round2:
                ofile = wp.workdir / insn.working_dir / f"mutation-testing.round2.{args.r2source}.{args.experiment}.json"
            else:
                ofile = wp.workdir / insn.working_dir / f"mutation-testing.{args.experiment}.json"

            with open(ofile, "w") as f:
                json.dump(survivors, fp=f, indent='  ')
