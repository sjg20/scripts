#!/bin/sh

set -ex

#V=-v

# Run a test on ARM with qemu

test=$*

export CROSS_COMPILE=`buildman -A qemu-riscv64_spl`
#export OPENSBI=~/dev/riscv/riscv64-fw_dynamic.bin
# export OPENSBI=/scratch/sglass/opensbi-1.3.1-rv-bin/share/opensbi/ilp32/generic/firmware/fw_dynamic.bin
export OPENSBI=/scratch/sglass/opensbi-1.3.1-rv-bin/share/opensbi/lp64/generic/firmware/fw_dynamic.bin;
PATH=$PATH:/vid/software/devel/ubtest/u-boot-test-hooks/ test/py/test.py \
	-B qemu-riscv64_spl --id na --build-dir /tmp/b/qemu-riscv64_spl \
	--build -k "${test}"
