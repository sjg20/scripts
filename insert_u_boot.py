# Put U-Boot into an image at a given offset

image = '/home/sglass/cosarm/chroot/build/coral/firmware/image-coral.serial.bin'
u_boot = '/tmp/b/chromebook_coral/u-boot.bin'
out = 'cb.bin'
pos = 0xffef1000 - 0xff000000

with open(image, 'rb') as fd:
	indata = fd.read()
with open(u_boot, 'rb') as fd:
	ubdata = fd.read()

data = indata[:pos]
data += ubdata
data += indata[pos + len(ubdata):]

with open(out, 'wb') as fd:
	fd.write(data)
