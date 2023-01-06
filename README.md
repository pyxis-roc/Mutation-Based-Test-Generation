# Mutation Based Test Generation Pipeline

This repository contains the code and artifact for our paper Pai and
Shitrit, "Generating Test Suites for GPU Instruction Sets through
Mutation and Equivalence Checking", to be submitted to ACM TOSEM.

The directory `rocettaprep` contains all the scripts and code used in
this paper, questions about these to be directed to the first author
(Sreepathi Pai).

The directory `src` contains the scripts and code for the older
version of this paper published as a registered report in the FUZZING
workshop. Questions about this piece of code to be directed to the
second author (Shoham Shitrit).

# Contact Information

Shoham Shitrit, University of Rochester '22, sshitrit@u.rochester.edu, shohamshitrit1@gmail.com

Sreepathi Pai, University of Rochester, https://cs.rochester.edu/~sree/

# Requirements

This artifact requires around 350GB of disk space for a full
experiment.

It compiles and runs a very large number of files (> 6M) and a
multicore processor is highly recommended.

We used an AMD AMD EPYC 7502P 32-Core Processor on which full parallel
compilation took about 8 hours, and running the experiments took
around 15 hours (with 5 minute timeouts) or 5 hours (with the default
90 second timeouts). The system has 256GB of memory, though this is
not a memory intensive workload.

## Time Requirements

Running input generation from scratch (aka `--all`) on all
instructions is the most expensive experiment in terms of space and
time, taking around upwards of 3TB and maybe a week or more to run.

Running input generation from scratch for the `tallset.list` set of
instructions takes around 1.5TB and around 19--25 hours.

Running the standard pipeline on all instructions takes around 350GB
and around 17 hours.

Note this system has only been tested running everything to
completion. Although stages can be run individually, there is very
little software support to do so and ensure consistency.

## System software requirements

  - clang-7 (for MUSIC), see [its prerequisites](https://github.com/swtv-kaist/MUSIC) for a complete list.
  - clang-13
  - GCC (tested with 7.5.0 and 9.4.0)

The artifact has primarily been tested on Ubuntu 18.04.6 LTS and on
Ubuntu 20.04.5 LTS.

## Installing clang-13 on Ubuntu 20.04 LTS

On Ubuntu 20.04 LTS, `clang-13` can be installed from
https://apt.llvm.org/, using the following `/etc/apt/sources.list.d/llvm.list`

```
deb http://apt.llvm.org/focal/ llvm-toolchain-focal-13 main
deb-src http://apt.llvm.org/focal/ llvm-toolchain-focal-13 main
```

# Installation

We shall use a directory `$MUTHOME` to store all the source code and
tools. Another directory `$EXPTHOME` will be used to store the
generated files. We will use `$REPODIR` to refer to the directory in
which this repository has been cloned.

```
mkdir $MUTHOME
cd $MUTHOME

$REPODIR/sys-prereqs.sh
```

This should result in output like:
```
*** GCC version
gcc (Ubuntu 9.4.0-1ubuntu1~20.04.1) 9.4.0
Copyright (C) 2019 Free Software Foundation, Inc.
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

*** Clang version
Ubuntu clang version 13.0.1-++20220120110924+75e33f71c2da-1~exp1~20220120231001.58
Target: x86_64-pc-linux-gnu
Thread model: posix
InstalledDir: /usr/bin
*** Python 3 version
Python 3.8.10
```

If, instead, you get an error like this:

```
sys-prereqs.sh: line 12: clang-7: command not found
```

Install the prerequisite and rerun `sys-prereqs.sh`

## Install MUSIC

Run the `install-music.sh` script from within `$MUTDIR` to install the (MUSIC mutator)[https://github.com/swtv-kaist/MUSIC]:

```
$REPODIR/install-music.sh
```

This will clone MUSIC, and compile it (takes about 30 minutes).

After the process, you should see after executing `ls`:

```
lib MUSIC
```

## Create and Install Python Virtual Environment

The experimental scripts use [Parsl](https://github.com/Parsl/parsl),
[Polars](https://www.pola.rs/) and [SciPy](https://scipy.org), and
[Pycparser](https://github.com/eliben/pycparser).

The `install-venv.sh` script creates a Python virtual environment and
installs all the packages. Continue in `$MUTDIR`:

```
$REPODIR/install-venv.sh
```

This will create a directory called `parslenv`. Run the following
commands in `$MUTDIR` to make sure everything has worked.

```
source parslenv/bin/activate
$REPODIR/prereqs.py
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

# Setup the experimental directory

With the virtual environment all setup, run the following command in
`$MUTDIR` to setup the directory that will contain all the
experimental data (i.e. `$EXPTDIR`). This directory will grow to at
least 45GB.  From within the virtual environment (assuming the
ptx-semantics from ROCetta are in the path below):

```
$REPODIR/rocettaprep/setup_workdir.py --fake-includes pycparser-release_v2.21/utils/fake_libc_include/ $REPODIR/rocettaprep/ptx-semantics/v6.5/c/ptxc.c $EXPTDIR
```

You should see some output like this:
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

If you do `ls $EXPTHOME`, you should see:

```
params.json  ptxc_fake_includes  samplers
```

Setup is now done!

# The small set experiment

First, we'll run the experiments on a small set of instructions,
called the `smallset`. This is similar to the set used in the
registered report and should be a quick check that everything is
setup.

## Initial code generation and compilation

To create the tests, mutants, equivalence check drivers, mutation
testing drivers, outputs, etc, run the following command.

```
$REPODIR/rocettaprep/build.sh $REPODIR/rocettaprep/smallset $EXPTDIR
```

You should see messages like this slowly scroll by:

```
subc_cc_s32: Success.
sqrt_rm_f32: Success.
sqrt_rn_f32: Success.
abs_f32 mutants: Success.
add_rm_ftz_sat_f32 mutants: Success.
```

Correct execution of this command will produce in `exptdata`, a number
of `working-directory-*` directories, one for each
instruction. Within each instruction-level directory, there will be
directories for mutants (`music`), the equivalence checker drivers
(`eqchk`), the fuzzer drivers (`libfuzzer_simple`, and
`libfuzzer_custom`), and the known good outputs (`outputs`).

## Run the small set experiment, normal flow

Now, use the `run_expt.py` script to actually perform the experiment
as described in the paper. Note the "@" in `--insn`

```
$REPODIR/rocettaprep/run_expt.py --auto-no-json --insn @$REPODIR/rocettaprep/smallset $EXPTDIR smallsettest
```

This will run all the experiments for Table 2 and Table 3 and store
the results in `$EXPTDIR/expt.smallsettest/*.csv` for later processing
by the scripts. It should take no more than a few minutes.

## Run the small set experiment to generate inputs from scratch

The `run_expt.py` script can be used to generate inputs completely
from scratch as described in the paper. Use the `--all` option and a
different experiment name

```
$REPODIR/rocettaprep/run_expt.py --auto-no-json --insn @$REPODIR/rocettaprep/smallset $EXPTDIR scratch --all
```

This will run all the experiments for Table 4 (input generation from
scratch) and store the results in `$EXPTDIR/expt.smallsettest/*.csv`
for later processing by the scripts. It should take no more than a few
minutes.


# The full set experiment

Use the following commands to build and run the experiments for the
full set of instructions.

```
$REPODIR/rocettaprep/build.sh $REPODIR/rocettaprep/all_insns.list $EXPTDIR

$REPODIR/rocettaprep/run_expt.py --auto-no-json --insn @$REPODIR/rocettaprep/all_insns.list $EXPTDIR fullset

$REPODIR/rocettaprep/run_expt.py --auto-no-json --insn @$REPODIR/rocettaprep/all_insns.list --all $EXPTDIR allfullset
```

Note the first step here can take around 8 hours, and the other steps can take around 5 hours each.
