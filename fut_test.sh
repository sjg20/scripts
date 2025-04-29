#!/bin/bash

set -ex

fut=futility
kd=~/u/cros/data/devkeys
#debug=--debug
rom=/tmp/b/chromeos_coral/image.bin

cp /tmp/b/chromeos_coral/spl/u-boot-spl.bin fv

test() {
	# sign it
	echo sign
	$fut $debug vbutil_firmware \
		--signprivate $kd/firmware_data_key.vbprivk \
		--keyblock $kd/firmware.keyblock \
		--vblock vb \
		--kernelkey $kd/kernel_subkey.vbpubk \
		--version 1 \
		--flags 0 \
		--fv fv
	echo

	$fut gbb --rootkey rk.bin $rom

	# check it
	echo check
	$fut $debug vbutil_firmware \
		--verify vb \
		--keyblock $kd/firmware.keyblock \
		--signpubkey rk.bin \
		--kernelkey kk \
		--fv fv
}

test_coral() {
	rom=~/cosarm/chroot/build/coral/firmware/image-coral.bin
	$fut gbb --rootkey rk.bin $rom
}

test
# test_coral
