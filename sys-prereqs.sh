#!/bin/bash

set -e

echo "*** GCC version"
gcc --version

echo "*** Clang-13 version"
clang-13 --version

echo "*** Clang-7 version"
clang-7 --version

echo "*** Python 3 version"
python3 --version

echo "===> DONE <==="

