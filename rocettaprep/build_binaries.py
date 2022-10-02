#!/usr/bin/env python
#

import argparse

from parsl.app.app import python_app, bash_app
import parsl
from build_single_insn import Insn
from rocprepcommon import *
from parsl.app.errors import BashExitFailure
from parsl.dataflow.error import DependencyError
import sys
import os

@bash_app
def make_oracle(wp, insn, stderr=parsl.AUTO_LOGNAME, stdout=parsl.AUTO_LOGNAME, label = None):
    return f'make -C {wp.workdir / insn.working_dir}'

@bash_app
def make_outputs(oracle, wp, insn, stderr=parsl.AUTO_LOGNAME, stdout=parsl.AUTO_LOGNAME, label = None):
    x = os.cpu_count()
    return f'make -C {wp.workdir / insn.working_dir} -f Makefile.outputs -j {x}'

@bash_app
def make_mutants(wp, insn, mutant="music", stderr=parsl.AUTO_LOGNAME, stdout=parsl.AUTO_LOGNAME, label = None):
    x = os.cpu_count()
    return f'make -C {wp.workdir / insn.working_dir / mutant} -j {x} -k'

def get_ba_result(header, ba):
    try:
        # for some reason, this does not catch parsl.app.error.BashAppNoReturn,
        # but it is logged to parsl.log.

        res = ba.result()
        if res == 0:
            print(f"{header}: Success.")
        return True
    except BashExitFailure as e:
        # exits with code 2 indicate compiler failures. With mutants, this is normal.
        print(f"{header}: Failed with code {e.exitcode}")
    except DependencyError as e:
        print(f"{header}: Workflow failed. Examine logs in runinfo (usually).")

    return False

if __name__ == "__main__":
    from setup_workdir import WorkParams
    from runconfig import config

    p = argparse.ArgumentParser(description="Create the oracle binary, the mutant binaries, and oracle outputs")

    p.add_argument("workdir", help="Work directory")
    p.add_argument("--insn", help="Instructions to process, '@FILE' form loads list from file instead")

    args = p.parse_args()
    insns = get_instructions(args.insn)

    if len(insns) == 0:
        print("ERROR: An instruction must be specified. Use --insn")
        sys.exit(1)

    parsl.load(config)

    wp = WorkParams.load_from(args.workdir)

    out = []
    for i in insns:
        insn = Insn(i)
        r = make_oracle(wp, insn, label=i)
        out.append((i, r))

    out2 = []
    for i, r in out:
        # also -j
        r2 = make_outputs(r, wp, Insn(i), label=i)
        if get_ba_result(i, r2):
            out2.append(i)

    for i in out2:
        # run mutants one at a time, since make -j
        insn = Insn(i)
        m = make_mutants(wp, insn, label=i)
        get_ba_result(i + " mutants", m)
