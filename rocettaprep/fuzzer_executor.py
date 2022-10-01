from runcommon import run_and_time
import sys

class FuzzerExecutor:
    def __init__(self, wp, experiment, subset = '', timeout_s = 90):
        self.wp = wp
        self.experiment = experiment
        self.subset = subset
        self.timeout_s = timeout_s

    def make(self, mutant_exec):
        p = mutant_exec.parent
        t = mutant_exec.name

        print(f"{mutant_exec}: Compiling executable", file=sys.stderr)
        r, tm = run_and_time(["make", "-C", str(p), t])
        print(f"{mutant_exec}: Compilation took {tm/1E6} ms", file=sys.stderr)
        return r.returncode

    def run(self, insn, mutant):
        if self.subset:
            subset = 'all.'
        else:
            subset = ''

        # this can make running repeats painful.
        odir = mutant.parent / f"fuzzer_output.{mutant.name}.{subset}{self.experiment}"

        cmd = [str(mutant), f"-exact_artifact_path={odir}"]

        # run make always to ensure correct binaries
        r = self.make(mutant)
        if not (r == 0):
            print(f"{mutant}:ERROR: Compilation appears to have failed. Continuing anyway.",
                  file=sys.stderr)

        print(f"{mutant}: {' '.join(cmd)}", file=sys.stderr)

        try:
            r, t = run_and_time(cmd, timeout_s = self.timeout_s)
            if t is not None:
                print(f"{mutant}:{subset}{self.experiment}: Total fuzzing time {t/1E6} ms, retcode = {r.returncode}", file=sys.stderr)
            else:
                print(f"{mutant}:{subset}{self.experiment}: Fuzzing timed out", file=sys.stderr)

            return {'time_ns': t, 'retcode': r.returncode}
        except FileNotFoundError:
            print(f"ERROR: {mutant} does not exist.", file=sys.stderr)
            return None

        assert False
