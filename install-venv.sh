#!/bin/bash

set -e

# unfortunately if this script halts in between, need to remove
# parslenv/ and start again.

[ -d parslenv ] || python3 -m venv parslenv

if source parslenv/bin/activate; then
    # versions indicated tested variants

    pip install pycparser==2.21 # hard req
    pip install parsl==1.2.0    # probably not a hard req
    pip install polars==0.14.9  # probably not a hard req
    pip install scipy==1.9.1    # probably not a hard req
    pip install pyyaml

    # for the fake includes
    [ ! -d pycparser-release_v2.21 ] && wget https://github.com/eliben/pycparser/archive/refs/tags/release_v2.21.tar.gz && tar axf release_v2.21.tar.gz
fi;
