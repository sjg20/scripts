#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0+
#
# Copyright 2021 Google LLC
#

from argparse import ArgumentParser
import camel_case
import glob
import os
import re

RE_FUNC = re.compile(r' *def (\w+)\(')

def collect_funcs(fname):
    with open(fname, encoding='utf-8') as inf:
        data = inf.read()
        funcs = RE_FUNC.findall(data)
    return data, funcs

def get_module_name(fname):
    """Convert a filename to a module name

    Args:
        fname (str): Filename to convert, e.g. 'tools/patman/tools.py'

    Returns:
        str: Module name, e.g. 'patman.tools'
    """
    parts = os.path.splitext(fname)[0].split('/')[1:]
    module_name = '.'.join(parts)
    return module_name, parts[-1]

def process(srcfile, do_write):
    data, funcs = collect_funcs(srcfile)
    module_name, leaf = get_module_name(srcfile)
    print('module_name', module_name)
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
            newdata, count = re.subn(r'%s.%s\(' % (leaf, name),
                                     f'{leaf}.{new_name}(', data)
            total += count
            data = newdata

        imports = re.findall(r'from %s import (.*)\n' % module_name, data)
        for item in imports:
            #print('item', item)
            names = [n.strip() for n in item.split(',')]
            new_names = [conv.get(n) or n for n in names]
            print('names', names, new_names)
            new_line = 'from %s import %s\n' % (module_name,
                                                ', '.join(new_names))
            data = re.sub(r'from %s import (.*)\n' % module_name, new_line,
                          data)

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
