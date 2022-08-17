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


def compare(test_info):
    output_file = test_info.tmp_output.get_name()
    gold_file = test_info.gold_output

    r = subprocess.run(['diff', '-q', str(output_file), str(gold_file)])
    return r.returncode == 0

def run_single_test(test_info):
    cmdline = [x if not isinstance(x, TempFile) else x.get_name() for x in test_info.cmdline]

    try:
        r = subprocess.run(cmdline, check=True)
        return compare(test_info)
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        # missing binaries should be handled differently?
        return False

def run_tests(wp, insn):
    tt = InsnTest(wp, insn)
    tt.load_tests()

    workdir = wp.workdir / insn.working_dir

    # TODO: support other mutants?
    with open(workdir / "music.json", "r") as f:
        mutants = json.load(fp=f)

    out = []
    for mut in mutants:
        for test in tt.gen_tests(binary = workdir / mut['target']):
            res = run_single_test(test)
            if not res: break
        else:
            # mutant survived tests
            out.append(mut['src'])

    return out

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Run tests on mutants")

    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")

    args = p.parse_args()
    insns = get_instructions(args.insn)

    if len(insns):
        wp = WorkParams.load_from(args.workdir)

        for i in insns:
            insn = Insn(i)
            survivors = run_tests(wp, insn)
            print(f"{len(survivors)} survivors for {i}")
            with open(wp.workdir / insn.working_dir / f"mutation-testing.{args.experiment}.json", "w") as f:
                json.dump(survivors, fp=f, indent='  ')
