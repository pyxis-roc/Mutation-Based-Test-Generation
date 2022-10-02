#!/usr/bin/env python3

import sys
import os
from pathlib import Path

venv = os.environ.get('VIRTUAL_ENV', '')

if venv == "":
    print("WARNING: No virtual env detected.")
else:
    print(f"Virtual Env in {venv} detected.")

try:
    import parsl
    print(f"Parsl version: {parsl.__version__}")
except ImportError:
    print(f"Parsl NOT FOUND")
    sys.exit(1)

try:
    import scipy
    print(f"scipy version: {scipy.__version__}")
except ImportError:
    print(f"SciPy NOT FOUND")
    sys.exit(1)

try:
    import polars
    print(f"polars version: {polars.__version__}")
except ImportError:
    print(f"polars NOT FOUND")
    sys.exit(1)

try:
    import pycparser
    print(f"pycparser version: {pycparser.__version__}")
except ImportError:
    print(f"pycparser NOT FOUND")
    sys.exit(1)


print(f"Assuming {os.curdir} is $MUTDIR, looking for pycparser-release_v2.21")
p = Path(os.curdir) / 'pycparser-release_v2.21'
if p.exists():
    print(f"FOUND: {p}")
else:
    print(f"NOT FOUND: {p}")
    sys.exit(1)

print("ALL OK")
