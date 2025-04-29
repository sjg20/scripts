# True: Put bootblock first, so it boots into TPL
# False: Put TPL first, so it boots into bootblock
bb_first = True

bootblock = '/home/sglass/cosarm/chroot/build/coral/firmware/coral/coreboot_serial/bootblock.bin'
tpl = '/tmp/b/chromebook_coral/tpl/u-boot-tpl.bin'
out = 'merged.bin'

with open(bootblock, 'rb') as fd:
	bb_data = fd.read()

with open(tpl, 'rb') as fd:
	tpl_data = fd.read()

if bb_first:
	data = bb_data[:0x4000]
	data += tpl_data
	data += bb_data[0x4000 + len(tpl_data):]
else:
	data = tpl_data
	data += b'\0' * (0x4000 - len(data))
	data += bb_data
	data = data[:0x7ff1] + b'\x80' + data[0x7ff2:]

with open(out, 'wb') as fd:
	fd.write(data)
