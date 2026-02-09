#! /bin/bash

rpm2cpio "$1" | cpio --quiet -dim "$2"

if [[ "$1" == *"debuginfo"* ]]; then
    if [ -d "./usr/lib/debug/boot/" ]; then
        mv ./usr/lib/debug/boot/* ..
    fi
fi

mv $2 ../
