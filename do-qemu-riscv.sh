#!/bin/sh

set -ex

#V=-v

# Run a test on ARM with qemu

test=$*

crosfw qemu-riscv32
PATH=$PATH:/vid/software/devel/ubtest/u-boot-test-hooks/ test/py/test.py \
	-B qemu-riscv32 --id na --build-dir /tmp/b/qemu-riscv32 -k "${test}"
