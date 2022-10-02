#!/bin/bash

set -e

UVER=20.04 # change this to 18.04 if needed

if  ! which cbmc ; then
    [ -f ubuntu-$UVER-cbmc-5.38.0-Linux.deb ] || wget "https://github.com/diffblue/cbmc/releases/download/cbmc-5.38.0/ubuntu-$UVER-cbmc-5.38.0-Linux.deb"
    sudo dpkg -i ubuntu-$UVER-cbmc-5.38.0-Linux.deb
fi;

if ! which z3 ; then
    F=z3-4.8.16-x64-glibc-2.31.zip
    [ -f $F ] || wget "https://github.com/Z3Prover/z3/releases/download/z3-4.8.16/$F"
    [ -f z3-4.8.16-x64-glibc-2.31 ] || unzip $F

    # this assumes ~/.local/bin is in PATH, which it usually is.

    mkdir -p ~/.local/bin

    if [ ! -f ~/.local/bin/z3 ]; then
        ln -sr z3-4.8.16-x64-glibc-2.31/bin/z3 ~/.local/bin/
    fi;
fi;

which cbmc && echo "==> CBMC installed <=="
( which z3  && echo "==> Z3 installed <==" ) || ( [ -f ~/.local/bin/z3 ] && echo "Z3 installed, but not in PATH, you may have to logout and log back in to add ~/.local/bin to your PATH" ) || echo "Z3 not installed"
