#!/bin/sh

set -ex

#V=-v

# Run a test on ARM with qemu

test=$*

export CROSS_COMPILE=`buildman -A qemu-riscv64_spl`
export OPENSBI=~/dev/riscv/riscv64-fw_dynamic.bin
PATH=$PATH:/vid/software/devel/ubtest/u-boot-test-hooks/ test/py/test.py \
	-B qemu-riscv64 --id na --build-dir /tmp/b/qemu-riscv64_spl \
	--build -k "${test}"
