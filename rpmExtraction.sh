#! /bin/bash

rpm2cpio $1 | cpio -dium $2
mv $2 .
