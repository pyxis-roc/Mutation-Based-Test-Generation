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
import runcommon

import time

def run_single_test(wp, insn, test_info):
    def compare(wp, insn, test_info):
        output_file = test_info.tmp_output.get_name()
        gold_file = wp.workdir / insn.working_dir / "outputs" / test_info.gold_output.name

        r = subprocess.run(['diff', '-q', str(output_file), str(gold_file)])
        return r.returncode == 0

    cmdline = [x if not isinstance(x, TempFile) else x.get_name() for x in test_info.cmdline]

    try:
        #r = subprocess.run(cmdline, check=True)
        r, time_ns = runcommon.run_and_time(cmdline, check=True)
        print(f"{insn.insn}:{test_info.cmdline[0]}: Mutant took {time_ns / 1E6} ms")
        return compare(wp, insn, test_info)
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        # missing binaries should be handled differently?
        return False

@python_app
def run_tests_on_mutant(wp, insn, mut, tt, muthelper, filter_fn):
    workdir = wp.workdir / insn.working_dir

    start = time.monotonic_ns()

    for test in tt.gen_tests(binary = workdir / muthelper.srcdir / mut['target'],
                             filter_fn = filter_fn):

        res = run_single_test(wp, insn, test)

        for x in test.cmdline:
            if isinstance(x, TempFile): x.cleanup()

        if not res:
            end = time.monotonic_ns() # ugly
            break
    else:
        # mutant survived tests
        end = time.monotonic_ns()
        return {'time_ns': end - start, 'result': mut['src']}

    # mutant was killed
    return {'time_ns': end - start, 'result': None}

def run_tests(wp, insn, muthelper, experiment, round2 = False, r2source = 'eqvcheck', all_subset = False):
    tt = InsnTest(wp, insn)
    tt.load_tests()

    workdir = wp.workdir / insn.working_dir
    mutants = muthelper.get_mutants(insn)

    # we end up running on all non-equivalent mutants
    # which because of the way eqvcheck is setup are only survivors from round1
    # or all except equivalent (--all).

    if all_subset:
        assert round2, "all_subset=True needs round2=True"
        subset = 'all.'
    else:
        subset = ''

    if round2:
        with open(workdir / f"eqvcheck_results.{subset}{experiment}.json") as f:
            non_eq_mutants = set(json.load(fp=f))

        mutants = [x for x in mutants if x['src'] in non_eq_mutants]

        if r2source == 'eqvcheck':
            filter_fn = lambda x: x[1]['source'] == f'{subset}eqvcheck.{experiment}'
        elif r2source == 'fuzzer_simple':
            filter_fn = lambda x: x[1]['source'] == f'{subset}libfuzzer_simple.{experiment}'
        elif r2source == 'fuzzer_custom':
            filter_fn = lambda x: x[1]['source'] == f'{subset}libfuzzer_custom.{experiment}'
        else:
            raise NotImplementedError(f"Unrecognized r2source '{r2source}'")
    else:
        # don't use tests generated by translation validator (verifyce)
        # or by eqvcheck or by fuzzers
        filter_fn = lambda x: x[1]['source'] == f'gen_tests'

    out = []
    for mut in mutants:
        res = run_tests_on_mutant(wp, insn, mut, tt, muthelper, filter_fn)
        out.append((mut['target'], res))

    out = [(p, res.result()) for (p, res) in out]

    if round2:
        timdat = f"mutant_timing.{subset}{experiment}.{r2source}.json"
    else:
        timdat = f"mutant_timing.{experiment}.json"

    with open(workdir / timdat, "w") as f:
        json.dump(dict(out), fp=f)

    surv = [x['result'] for _, x in out if x['result'] is not None]
    return surv

if __name__ == "__main__":
    from setup_workdir import WorkParams
    from runconfig import config

    p = argparse.ArgumentParser(description="Run tests on mutants")

    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("--mutator", choices=get_mutators(), default="MUSIC")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")
    p.add_argument("--round2", help="Second round, so run only on survivors using tests generated by eqvcheck or the fuzzer", action='store_true')
    p.add_argument("--r2source", help="Source for second round tests", choices=['eqvcheck', 'fuzzer_simple', 'fuzzer_custom'], default='eqvcheck')
    p.add_argument("--all", help="Use the --all subset", action="store_true")

    args = p.parse_args()
    insns = get_instructions(args.insn)

    if args.all and not args.round2:
        print("ERROR: --round2 must be specified for --all, for internal reasons")
        sys.exit(1)

    parsl.load(config)

    if args.all:
        subset = 'all.'
    else:
        subset = ''

    if len(insns):
        wp = WorkParams.load_from(args.workdir)
        muthelper = get_mutation_helper(args.mutator, wp)

        for i in insns:
            insn = Insn(i)
            survivors = run_tests(wp, insn, muthelper, args.experiment, args.round2, args.r2source, args.all)
            print(f"{len(survivors)} survivors for {i}")

            if args.round2:
                ofile = wp.workdir / insn.working_dir / f"mutation-testing.round2.{args.r2source}.{subset}{args.experiment}.json"
            else:
                ofile = wp.workdir / insn.working_dir / f"mutation-testing.{args.experiment}.json"

            with open(ofile, "w") as f:
                json.dump(survivors, fp=f, indent='  ')
