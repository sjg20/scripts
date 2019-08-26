#!/usr/bin/python

import sys

last = None

for line in sys.stdin.readlines():
  line = line.strip()
  if not line:
    continue
  addr, name = line.split()
  if last:
    size = int(addr, 16) - last[0]
    print size, last[1][1:-2]
  last = [int(addr, 16), name]
