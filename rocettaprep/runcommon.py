#!/usr/bin/env python3

import subprocess
import time

def run_and_time(cmd, check=False, stdout=None, stderr=None, timeout_s = None):
    if timeout_s is not None:
        cmd = ["timeout", str(timeout_s)] + cmd

    start = time.monotonic_ns()
    obj = subprocess.run(cmd, check=check,
                         stdout=stdout,
                         stderr=stderr)
    end = time.monotonic_ns()

    if timeout_s is not None and (obj.returncode == 124 or obj.returncode == 128+9):
        # timed out
        return obj, None

    return obj, end - start
