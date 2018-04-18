#! /bin/bash

rpm2cpio $1 | cpio -dium $2
mv $2 .
if [[ $1 = *"debuginfo"* ]]; then
	mv ./lib/debug/boot/* .
fi
