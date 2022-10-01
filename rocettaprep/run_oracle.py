#!/usr/bin/env python3
#
# run_oracle.py
#
# Check if the oracle passes the tests on generated inputs. This is
# primarily to help detect issues with the eqvcheck-generated outputs
# (which don't use the oracle) or to shake out any non-determinism
# issues.

import subprocess
import argparse
from roctest import *
from rocprepcommon import *
from build_single_insn import Insn
import json
import subprocess
from parsl.app.app import python_app, join_app
import parsl
import runcommon

import time
import sys

def run_single_test(wp, insn, test_info):
    def compare(wp, insn, test_info):
        output_file = test_info.tmp_output.get_name()
        gold_file = wp.workdir / insn.working_dir / "outputs" / test_info.gold_output.name

        r = subprocess.run(['diff', '-q', str(output_file), str(gold_file)])
        return r.returncode == 0

    cmdline = [x if not isinstance(x, TempFile) else x.get_name() for x in test_info.cmdline]

    try:
        r, time_ns = runcommon.run_and_time(cmdline, check=True, timeout_s=10)
        if time_ns is not None:
            msg = f"{insn.insn}:{test_info.cmdline[0]}: Oracle took {time_ns / 1E6} ms"
            print(msg, file=sys.stderr)
            return compare(wp, insn, test_info), msg
        else:
            msg = f"{insn.insn}:{test_info.cmdline[0]}: Oracle timed out"
            print(msg, file=sys.stderr)
            return False, msg
    except subprocess.CalledProcessError:
        return False, f"{insn.insn}:{test_info.cmdline[0]}: CalledProcessError"
    except FileNotFoundError:
        # missing binaries should be handled differently?
        return False, f"{insn.insn}:{test_info.cmdline[0]}: FileNotFoundError"

@python_app
def run_tests_on_oracle(wp, insn, tt, filter_fn):
    from run_oracle import run_single_test
    import time
    from roctest import TempFile

    workdir = wp.workdir / insn.working_dir

    start = time.monotonic_ns()

    for test in tt.gen_tests(binary = workdir / insn.test_file[:-2], # drop the .c
                             filter_fn = filter_fn):

        res, msg = run_single_test(wp, insn, test)

        for x in test.cmdline:
            if isinstance(x, TempFile): x.cleanup()

        # this only returns the first output that fails ...
        if not res:
            return False, test.gold_output

    # oracle survived all tests, as it should
    return True, None

@python_app
def finish_tests_on_oracle(workdir, experiment, inputs=[]):
    import json

    out = [str(output.name) for survived, output in inputs if not survived]

    dat = f"oracle_check.{experiment}.json"

    with open(workdir / dat, "w") as f:
        json.dump(list(out), fp=f)

    return out

@join_app
def run_tests(wp, insn, experiment):
    import json
    from roctest import InsnTest

    tt = InsnTest(wp, insn)
    tt.load_tests()

    workdir = wp.workdir / insn.working_dir

    filter_fn = lambda x: x[1]['source'].endswith(f'.{experiment}')

    out = []
    res = run_tests_on_oracle(wp, insn, tt, filter_fn)
    return finish_tests_on_oracle(workdir, experiment, inputs=[res])

if __name__ == "__main__":
    from setup_workdir import WorkParams
    from runconfig import htconfig

    p = argparse.ArgumentParser(description="Run tests on mutants")

    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")

    args = p.parse_args()
    insns = get_instructions(args.insn)

    parsl.load(htconfig)

    if len(insns):
        pt = PrepTimer()
        pt.start_timer()

        wp = WorkParams.load_from(args.workdir)

        out = []
        for i in insns:
            insn = Insn(i)
            killed = run_tests(wp, insn, args.experiment)
            out.append((insn, killed))

        for _insn, _kf in out:
            _killed = _kf.result()
            res = "killed" if len(_killed) > 0 else "survived"
            print(f"{_insn.insn}: Oracle {res}", file=sys.stderr)
            if len(_killed) > 0:
                print(f"  {_insn.insn}", " ".join(_killed), file=sys.stderr)

        pt.end_timer()
