#!/usr/bin/env python3
#
# build_test_info.py
#
# Extracts per-instruction test cases information from
# instructions.yaml and stores it in the work directory.
#

import argparse
import yaml
import json

from rocprepcommon import *
from build_single_insn import Insn

def extract_insn_test_info(wp, insn_info, insn):
    od = wp.workdir / insn.working_dir

    # json is faster
    with open(od / "testcases.json", "w") as f:
        json.dump(insn_info, fp=f, indent='  ')

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="Extract and store testcases information in the work directory")
    p.add_argument("workdir", help="Work directory")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")

    args = p.parse_args()
    insns = get_instructions(args.insn)

    if len(insns):
        wp = WorkParams.load_from(args.workdir)

        yii = wp.tests_dir / 'instructions.yaml'

        with open(yii, "r") as f:
            insn_info = yaml.safe_load(f)
            iid = dict([(i['insn'], i) for i in insn_info])

            assert len(insn_info) == len(iid), f"Duplicate instructions in instructions.yaml"

        for i in insns:
            insn = Insn(i)
            extract_insn_test_info(wp, iid[i], insn)
