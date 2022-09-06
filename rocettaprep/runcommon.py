#!/usr/bin/env python3

import subprocess
import time

def run_and_time(cmd, check=False, stdout=None, stderr=None, timeout_s = None):
    if timeout_s is not None:
        cmd = ["timeout", str(timeout_s)] + cmd

    try:
        start = time.monotonic_ns()
        obj = subprocess.run(cmd, check=check or (timeout_s is not None),
                             stdout=stdout,
                             stderr=stderr)
        end = time.monotonic_ns()
        return obj, end - start

    except subprocess.CalledProcessError as e:
        if timeout_s is not None:
            if e.returncode == 124 or e.returncode == 128+9:
                return obj, None
            else:
                raise e
        else:
            raise e
