This is the artifact to accompany the our paper Pai and Shitrit,
"Generating Test Suites for GPU Instruction Sets through Mutation and
Equivalence Checking", submitted to ACM TOSEM.

The code for this paper lives in
[GitHub](https://github.com/pyxis-roc/Mutation-Based-Test-Generation)
in the `fullscale` branch. The artifact code is in the `artifact`
branch.

This artifact additionally contains:

  1. A subset of the PTX semantics from the ROCetta project.
  2. The data files from our experiments.

This README is based on the README.md in the
`Mutation-Based-Test-Generation` directory, which provides more
general instructions. The instructions in this file have been
simplified by fixing many of the paths used in those instructions.

This artifact has been tested on Ubuntu 18.04 LTS and 20.04 LTS. The
timing descriptions in this document were obtained from a 32-core AMD
EPYC machine.

## Unpacking

Unpack the artifact archive in location with around 50GB of free
space. We'll refer to this location as `$ARTIFACT`. All commands below
will be executed, unless otherwise noted, are executed from this location.

After unpacking, you should see the following files:

  - README, this file
  - LICENSE, the license for the contents of this artifact
  - REQUIREMENTS.md, a more detailed list of requirements and installation instructions
  - STATUS, detailing the artifact badges applied for.
  - INSTALL, superseded by this file.
  - Mutation-Based-Test-Generation, directory containing the source code for our paper
  - ROCetta-ptx-semantics, directory containing the PTX instruction semantics
  - Data, directory containing the data from our experiments, see the README in that directory for more details.

## System Requirements Check

Run `./Mutation-Based-Test-Generation/sys-prereqs.sh`. You should see:

```
*** GCC version
gcc (Ubuntu 9.4.0-1ubuntu1~20.04.1) 9.4.0
Copyright (C) 2019 Free Software Foundation, Inc.
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

*** Clang-13 version
Ubuntu clang version 13.0.1-++20220120110924+75e33f71c2da-1~exp1~20220120231001.58
Target: x86_64-pc-linux-gnu
Thread model: posix
InstalledDir: /usr/bin
*** Clang-13 version
clang version 7.0.1-12 (tags/RELEASE_701/final)
Target: x86_64-pc-linux-gnu
Thread model: posix
InstalledDir: /usr/bin
*** Python 3 version
Python 3.8.10
===> DONE <===
```

If you instead encounter errors, read the [REQUIREMENTS](REQUIREMENTS.md) file to install the system pre-requisites.

## MUSIC Installation

First, install all MUSIC pre-requisites (from https://github.com/swtv-kaist/MUSIC, an abridged list is below):

```
sudo apt-get install clang-7 clang-tools-7 libclang-common-7-dev libclang-7-dev libclang1-7 clang-format-7 python-clang-7 libllvm-7-ocaml-dev libllvm7 llvm-7 llvm-7-dev llvm-7-runtime
```

Run `./Mutation-Based-Test-Generation/install-music.sh` to download, compile, and setup the MUSIC installation.

After the compile, you should have `lib` (a symlink, required for
clang tools to locate their compiler headers) and a `MUSIC` directory
containing the MUSIC binary.

## Python Package Installation

The experimental scripts use [Parsl](https://github.com/Parsl/parsl),
[Polars](https://www.pola.rs/) and [SciPy](https://scipy.org), and
[Pycparser](https://github.com/eliben/pycparser).

Run `./Mutation-Based-Test-Generation/install-venv.sh` to create a Python virtual environment and install all the packages.

This will create a directory called `parslenv`. Run the following
commands to make sure everything has worked.

```
source parslenv/bin/activate
./Mutation-Based-Test-Generation/prereqs.py
```

You should see output that looks like this:

```
Virtual Env in /tmp/muthome/parslenv detected.
Parsl version: 1.2.0
scipy version: 1.9.1
polars version: 0.14.9
pycparser version: 2.21
Assuming . is $MUTDIR, looking for pycparser-release_v2.21
FOUND: pycparser-release_v2.21
ALL OK
```

All commands below now run in this virtual environment.

## Experimental Work Directory Setup

With the virtual environment all setup, run the following command to
setup a `exptdata` directory that will contain all the experimental data. This
directory will grow to at least 45GB.  From within the virtual
environment:

```
./Mutation-Based-Test-Generation/rocettaprep/setup_workdir.py --fake-includes pycparser-release_v2.21/utils/fake_libc_include/ ./ROCetta-ptx-semantics/v6.5/c/ptxc.c exptdata
```

You should see some output like this (the paths will be different):
```
cpp_args: '-DPYCPARSER -D__STDC_VERSION__=199901L -I/tmp/muthome/pycparser-release_v2.21/utils/fake_libc_include'
cpp_args: '-DPYCPARSER -D__STDC_VERSION__=199901L -I/tmp/muthome/pycparser-release_v2.21/utils/fake_libc_include'
<command-line>: warning: "__STDC_VERSION__" redefined
<built-in>: note: this is the location of the previous definition
/home/sree/src/mutation-testing/Mutation-Based-Test-Generation/rocettaprep/ptxc/ptxc.h:1:9: warning: #pragma once in main file
    1 | #pragma once
      |         ^~~~
...
Setup done
```

If you do `ls exptdata`, you should see:

```
params.json  ptxc_fake_includes  samplers
```

Setup is now done!

## The small set experiment

First, we'll run the experiments on a small set of instructions,
called the `smallset`. This is similar to the set used in the
registered report and should be a quick check that everything is
setup. Make sure you're still in the virtual environment for all the
commands below.

## Initial code generation and compilation

To create the tests, mutants, equivalence check drivers, mutation
testing drivers, outputs, etc, run the following command. .

```
./Mutation-Based-Test-Generation/rocettaprep/build.sh ./Mutation-Based-Test-Generation/rocettaprep/smallset exptdata
```

Note that you may see errors like this:

```
abs_f64 mutants: Failed with code 2
```

This is okay since not all mutants are semantically valid and the C
compiler will not compile them. The standard output and errors of the
compilation failures are available in the `runinfo/` directory created
by Parsl for inspection and debugging if necessary.

## Run the small set experiment, normal flow

Now, use the `run_expt.py` script to actually perform the experiment
as described in the paper, but on a smaller set of instructions. Note
the "@" in `--insn`

```
./Mutation-Based-Test-Generation/rocettaprep/run_expt.py --insn @./Mutation-Based-Test-Generation/rocettaprep/smallset exptdata smallset-test
```

This will run all the experiments for Table 2 and Table 3 and store
the results in `exptdata/expt.smallset-test/*.csv` for later processing
by the scripts. It should take around 10 minutes or so.

## Run the small set experiment to generate inputs from scratch

The `run_expt.py` script can be used to generate inputs completely
from scratch as described in the paper. Use the `--all` option and a
different experiment name

```
./Mutation-Based-Test-Generation/rocettaprep/run_expt.py --insn abs_f32 exptdata test-scratch --all
```

This will run all the experiments for Table 4 (input generation from
scratch) and store the results in
`exptdata/expt.smallset-scratch/*.csv` for later processing by the
scripts for the single instruction `abs_f32`. Although you can also use the full `smallset`, it will take much longer, on the order of an hour or so.

## Graphing the Data

TODO.

## The full set experiment

If the sets of experiments described in the previous two sections
worked, everything is setup properly and you can now run the full set
of experiments.

Use the following commands to build and run the experiments for the
full set of instructions.

```
./Mutation-Based-Test-Generation/rocettaprep/build.sh ./Mutation-Based-Test-Generation/rocettaprep/all_insns_except_cc exptdata

./Mutation-Based-Test-Generation/rocettaprep/run_expt.py --insn @./Mutation-Based-Test-Generation/rocettaprep/all_insns_except_cc exptdata fullset

./Mutation-Based-Test-Generation/rocettaprep/run_expt.py --insn @./Mutation-Based-Test-Generation/rocettaprep/all_insns_except_cc --all exptdata all-fullset
```

Note the first step here can take around 8 hours, and the other steps
can take around 5 hours each.

## Re-doing Experiments

Deleting the artifact directory and unpacking it should let you redo
everything from scratch.

