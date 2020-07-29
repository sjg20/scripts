# Put U-Boot into an image at a given offset

import os

u_boot = '/tmp/b/chromebook_coral/u-boot.rom'
outfile = '/tmp/asc'

def doit(name, pos, size):
    """Print out the crc32 value for a range from the ROM

    Args:
        name: Name of region
        pos: Position in ROM, starting at 0xff000000
        size: Size to checksum
    """
    base = 0xff000000
    offset = 0x81000
    pos -= base + offset
    with open(u_boot, 'rb') as fd:
        indata = fd.read()

    print('Extract from %x to %x' % (base + pos, base + pos + size))
    data = indata[pos:pos + size]

    with open(outfile, 'wb') as fd:
            fd.write(data)
    print('%s: ' % name, end='', flush=True)
    os.system('crc32 %s' % outfile)


doit('fsp-m', 0xff220000, 0x59000)
doit('fsp-s', 0xff279000, 0x2a000)

#59000 bytes from ff220000 to fef40000
