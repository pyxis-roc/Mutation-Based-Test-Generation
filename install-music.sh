#!/bin/bash

set -e

[ ! -d MUSIC ] && git clone https://github.com/swtv-kaist/MUSIC

# needed by all clang-tools to locate their headers

[ ! -f lib ] && ln -s /usr/lib

make -C MUSIC -j 4

