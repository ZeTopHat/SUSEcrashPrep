#! /bin/bash

rpm2cpio "$1" | cpio --quiet -dim "$2"

if [[ "$1" == *"debuginfo"* ]]; then
    Distro=$(rpm -qp $1 --qf %{Distribution})
    if [[ "$Distro" == *"16"* ]]; then
        mv ./usr/lib/debug/usr/lib/modules/*/vmlinux.debug ..
    elif [ -d "./usr/lib/debug/boot/" ]; then
        mv ./usr/lib/debug/boot/* ..
    fi
fi

mv $2 ../
