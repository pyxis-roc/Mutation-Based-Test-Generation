# Requirements

This artifact requires around 45GB of disk space for a full
experiment.

It compiles and runs a very large number of files (> 1M) and a
multicore processor is highly recommended.

We used an AMD AMD EPYC 7502P 32-Core Processor on which full parallel
compilation took about 8 hours, and running the experiments took
around 15 hours (with 5 minute timeouts) or 5 hours (with the default
90 second timeouts). The system has 256GB of memory, though this is
not a memory intensive workload.

## System software requirements

  - clang-7 (for MUSIC), see [its prerequisites](https://github.com/swtv-kaist/MUSIC) for a complete list.
  - clang-13
  - GCC (tested with 7.5.0 and 9.4.0)

The artifact has primarily been tested on Ubuntu 18.04.6 LTS and on
Ubuntu 20.04.5 LTS.

## Installing clang-13 on Ubuntu 20.04 LTS

On Ubuntu 20.04 LTS, `clang-13` can be installed from
https://apt.llvm.org/, using the following
`/etc/apt/sources.list.d/llvm.list`

```
deb http://apt.llvm.org/focal/ llvm-toolchain-focal-13 main
deb-src http://apt.llvm.org/focal/ llvm-toolchain-focal-13 main
```

## Checking requirements

Assuming you're in the root directory of the unpacked artifact archive, run:

```
./Mutation-Based-Test-Generation/sys-prereqs.sh
```

This should result in output like:
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

If, instead, you get an error like this:

```
sys-prereqs.sh: line 12: clang-7: command not found
```

Install clang-7 and rerun `sys-prereqs.sh`
