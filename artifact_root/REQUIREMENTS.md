# Requirements

This artifact requires around 45GB of disk space for a full
experiment. To run the input generation from scratch experiment
requires around 500GB of disk space.

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
  - z3 (tested with 4.8.16)
  - CBMC (tested with 5.38)
  - git

The artifact has primarily been tested on Ubuntu 18.04.6 LTS and on
Ubuntu 20.04.5 LTS. The scripts assume Ubuntu 20.04.

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

*** Clang-7 version
clang version 7.0.1-12 (tags/RELEASE_701/final)
Target: x86_64-pc-linux-gnu
Thread model: posix
InstalledDir: /usr/bin

*** Python 3 version
Python 3.8.10

*** CBMC version
5.48.0 (cbmc-5.48.0)

*** Z3 version
Z3 version 4.8.15 - 64 bit

*** diff version
diff (GNU diffutils) 3.7
Copyright (C) 2018 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

Written by Paul Eggert, Mike Haertel, David Hayes,
Richard Stallman, and Len Tower.

*** make version
GNU Make 4.2.1
Built for x86_64-pc-linux-gnu
Copyright (C) 1988-2016 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

*** timeout version
timeout (GNU coreutils) 8.30
Copyright (C) 2018 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

Written by Padraig Brady.

[... skipped ...]

===> DONE <===
```

Look for the `===> DONE <===` that indicates success. If, instead, you
get an error like this:

```
sys-prereqs.sh: line 12: clang-7: command not found
```

Install clang-7 and rerun `sys-prereqs.sh`

## Installing clang-13 on Ubuntu 20.04 LTS

On Ubuntu 20.04 LTS, `clang-13` can be installed from
https://apt.llvm.org/, using the following
`/etc/apt/sources.list.d/llvm.list`

```
deb http://apt.llvm.org/focal/ llvm-toolchain-focal-13 main
deb-src http://apt.llvm.org/focal/ llvm-toolchain-focal-13 main
```
## Installing CBMC and Z3 on Ubuntu 20.04 LTS

Run the script `install-tools.sh` to download and install CBMC and Z3.

CBMC will be installed system-wide and the scripts requires you to
have sudo permissions.

Z3 will be installed locally in to your `~/.local/bin` directory.

If you are running Ubuntu 18.04, modify the `UVER` variable to
download and install packages for Ubuntu 18.04.
