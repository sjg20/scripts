#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0+
#
# Copyright 2021 Google LLC
#

from argparse import ArgumentParser
import camel_case
import glob
import re

RE_FUNC = re.compile(r' *def (\w+)\(')

def collect_funcs(fname):
    with open(fname, encoding='utf-8') as inf:
        data = inf.read()
        funcs = RE_FUNC.findall(data)
    return data, funcs

def process(srcfile, do_write):
    data, funcs = collect_funcs(srcfile)
    #print(len(funcs))
    #print(funcs[0])
    conv = {}
    for name in funcs:
        conv[name] = camel_case.to_snake(name)
    for name, new_name in conv.items():
        #print(name, new_name)
        newdata, count = re.subn(r'%s\(' % name, f'%s(' % new_name, data)
        data = newdata
    if do_write:
        with open(srcfile, 'w', encoding='utf-8') as out:
            out.write(data)
    for fname in glob.glob('tools/**/*.py', recursive=True):
        with open(fname, encoding='utf-8') as inf:
            data = inf.read()
        total = 0
        for name, new_name in conv.items():
            newdata, count = re.subn(r'\.%s\(' % name, f'.%s(' % new_name, data)
            total += count
            data = newdata
        if total and do_write:
            with open(fname, 'w', encoding='utf-8') as out:
                out.write(data)


def main():
    epilog = 'Convert camel case function names to snake in a file and callers'
    parser = ArgumentParser(epilog=epilog)
    parser.add_argument('-s', '--srcfile', type=str, required=True, help='Filename to convert')
    parser.add_argument('-n', '--dry_run', action='store_true',
                        help='Dry run, do not write back to files')
    args = parser.parse_args()
    process(args.srcfile, not args.dry_run)

if __name__ == '__main__':
    main()
