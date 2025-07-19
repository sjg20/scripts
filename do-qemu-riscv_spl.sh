#!/bin/sh

set -ex

#V=-v

# Run a test on ARM with qemu

test=$*

OPENSBI=~/dev/riscv/opensbi/build/platform/generic/firmware/fw_dynamic.bin crosfw qemu-riscv32_spl
PATH=$PATH:/vid/software/devel/ubtest/u-boot-test-hooks/ test/py/test.py \
	-B qemu-riscv32_spl --id na --build-dir /tmp/b/qemu-riscv32_spl -k "${test}"
