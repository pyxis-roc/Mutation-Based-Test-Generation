#!/usr/bin/env python3
#
# separated out to aid pickling.
import itertools
from runcommon import run_and_time
import os
import sys

# https://github.com/diffblue/cbmc/blob/48893287099cb5780302fe9dc415eb6888354fd6/src/util/exit_codes.h
CBMC_RC_OK = 0
CBMC_RC_PARSE_ERROR = 2
CBMC_RC_CONV_ERROR = 6
CBMC_RC_VERIFICATION_UNSAFE = 10 # also conversion error when writing to other file.

class CBMCExecutor:
    def __init__(self, wp, experiment, subset = '', timeout_s = 90):
        self.wp = wp
        self.experiment = experiment
        self.subset = subset
        self.timeout_s = timeout_s

    def run(self, insn, mutant):
        xinc = list(zip(itertools.repeat("-I"), self.wp.include_dirs))

        if self.subset:
            subset = self.subset + '.'
        else:
            subset = ''

        ofile = mutant.parent / f"cbmc_output.{mutant.name}.{subset}{self.experiment}.json"
        # one more than most loops are expected to execute, removes spurious failures
        # due to unwinding assertion failures
        cmd = ["cbmc", "--unwind", str(65), "--unwinding-assertions", "--z3", "--json-ui", "--trace", "-I", str(self.wp.csemantics.parent)]
        cmd.extend(xinc)
        cmd.append(str(mutant))
        h = os.open(ofile, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode=0o666)
        print(" ".join(cmd), file=sys.stderr)
        r, t = run_and_time(cmd, stdout=h, timeout_s = self.timeout_s)
        if t is not None:
            print(f"{insn.insn}:{mutant}:{subset}{self.experiment}: Equivalence checker took {t/1E6} ms, retcode={r.returncode}", file=sys.stderr)
        else:
            print(f"{insn.insn}:{mutant}:{subset}{self.experiment}: Equivalence checker timed out, retcode={r.returncode}", file=sys.stderr)

        os.close(h)
        return {'time_ns': t, 'retcode': r.returncode}
