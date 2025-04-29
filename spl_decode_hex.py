#!/usr/bin/env python3

import sys

fd = open(sys.argv[1], 'r', encoding='utf-8')
data = b''
for line in fd:
    data += bytes([int(s, 16) for s in line.split()])
with open(sys.argv[2], 'wb') as outf:
    outf.write(data)
