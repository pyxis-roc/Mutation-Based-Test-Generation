#!/usr/bin/env python3

import argparse
import json
from rocprepcommon import *
from build_single_insn import Insn

if __name__ == "__main__":
    from setup_workdir import WorkParams

    p = argparse.ArgumentParser(description="")
    p.add_argument("workdir", help="Work directory")
    p.add_argument("experiment", help="Experiment name, must be suitable for embedding in filenames")
    p.add_argument("--insn", help="Instruction to process, '@FILE' form loads list from file instead")

    args = p.parse_args()
    insns = get_instructions(args.insn)

    if len(insns):
        wp = WorkParams.load_from(args.workdir)
        out = {}
        for i in insns:
            insn = Insn(i)
            with open(wp.workdir / insn.working_dir / "music.json", "r") as f:
                mutants = json.load(fp=f)

            with open(wp.workdir / insn.working_dir /
                      f"mutation-testing.{args.experiment}.json", "r") as f:
                data = json.load(fp=f)

                out[i] = {'survivors': len(data), 'mutants': len(mutants)}

        print(out)

