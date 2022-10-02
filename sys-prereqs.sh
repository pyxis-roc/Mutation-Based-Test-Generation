#!/bin/bash

set -e

echo "*** GCC version"
gcc --version

echo -e "*** Clang-13 version"
clang-13 --version

echo -e "\n*** Clang-7 version"
clang-7 --version

echo -e "\n*** Python 3 version"
python3 --version

echo -e "\n*** CBMC version"
cbmc --version

echo -e "\n*** Z3 version"
z3 --version

echo -e "\n*** diff version"
diff --version

echo -e "\n*** make version"
make --version

echo -e "\n*** timeout version"
timeout --version

echo -e "\n*** git version"
git --version

echo -e "\n*** ensurepip version"
python3 -m ensurepip --version

echo -e "\n*** wget version"
wget --version | head -1

echo -e "\n*** unzip version"
unzip -v | head -1

echo -e "\n*** sudo version"
sudo --version | head -1


echo "===> DONE <==="

