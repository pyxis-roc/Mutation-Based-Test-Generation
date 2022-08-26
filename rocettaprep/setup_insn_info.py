#!/usr/bin/env python
#
# setup_insn_info.py
#
# Copies instruction and test case information from ROCetta databases into JSON.
#
# This is an INTERNAL USE only script, at least, until ROCetta is released.

import sys
from rocprepcommon import load_instruction_list

try:
    from gpusemtest.isa.ptx import PTXInstructionInfo
except ImportError:
    print("ERROR: This is an internal prep script, intended to be run with ROCetta installed.", file=sys.stderr)
    sys.exit(1)

def prep_insn_info(insnlist):
    pii = PTXInstructionInfo.load(v=65)

    out = {}
    for i in insns:
        p = pii[i]
        out[i] = p.to_dict()

        del out[i]['name']

        for should_be_unset in ['base_instruction', 'testprop_key',
                                ]:
            assert out[i][should_be_unset] is None, out[i]
            del out[i][should_be_unset]

        for should_be_empty in ['postprocess', 'addrspace_in',
                                'addrspace_out', 'argflags_in',
                                'argflags_out', 'abstract_params',
                                'abstract_args', 'perthread_in',
                                'perthread_out']:
            assert len(out[i][should_be_empty]) == 0, out[i]
            del out[i][should_be_empty]

    return out

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Extract instruction and test case information from ROCetta KVDBs")
    p.add_argument("insnlist", help="List of instructions")
    p.add_argument("--oi", dest="insninfo", help="Output python file that will contain the instruction info database", default="insninfo.py")

    args = p.parse_args()
    insns = load_instruction_list(args.insnlist)

    with open(args.insninfo, "w") as f:
        print("## auto-generated", file=f)

        #TODO: line length
        print("insn_info = ", prep_insn_info(insns), file=f)
