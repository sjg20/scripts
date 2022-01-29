#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0+
#
# Copyright 2021 Google LLC
#

"""Changes the functions and class methods in a file to use snake case, updating
other tools which use them"""

from argparse import ArgumentParser
import glob
import os
import re
import subprocess

import camel_case

EXCLUDE_NAMES = set(['setUp', 'tearDown'])

RE_FUNC = re.compile(r' *def (\w+)\(')

def collect_funcs(fname):
    """Collect a list of functions in a file

    Args:
        fname (str): Filename to read

    Returns:
        tuple:
            str: contents of file
            list of str: List of function names
    """
    with open(fname, encoding='utf-8') as inf:
        data = inf.read()
        funcs = RE_FUNC.findall(data)
    return data, funcs

def get_module_name(fname):
    """Convert a filename to a module name

    Args:
        fname (str): Filename to convert, e.g. 'tools/patman/command.py'

    Returns:
        tuple:
            str: Full module name, e.g. 'patman.command'
            str: Leaf module name, e.g. 'command'
            str: Program name, e.g. 'patman'
    """
    parts = os.path.splitext(fname)[0].split('/')[1:]
    module_name = '.'.join(parts)
    return module_name, parts[-1], parts[0]

def process(srcfile, do_write, commit):
    data, funcs = collect_funcs(srcfile)
    module_name, leaf, prog = get_module_name(srcfile)
    print('module_name', module_name)
    #print(len(funcs))
    #print(funcs[0])
    conv = {}
    for name in funcs:
        if name not in EXCLUDE_NAMES:
            conv[name] = camel_case.to_snake(name)

    # Convert name to new_name in the file
    for name, new_name in conv.items():
        #print(name, new_name)
        # Don't match if it is preceeded by a '.', since that indicates that
        # it is calling this same function name but in a different module
        newdata, count = re.subn(r'(?<!\.)%s\(' % name, f'%s(' % new_name, data)
        data = newdata

        # But do allow self.xxx
        newdata, count = re.subn(r'self.%s\(' % name,
                                            f'self.%s(' % new_name, data)
        data = newdata
    if do_write:
        with open(srcfile, 'w', encoding='utf-8') as out:
            out.write(data)

    # Now find all files which use these functions and update them
    for fname in glob.glob('tools/**/*.py', recursive=True):
        with open(fname, encoding='utf-8') as inf:
            data = inf.read()
        total = 0

        # Update any simple functions calls into the module
        for name, new_name in conv.items():
            newdata, count = re.subn(r'%s.%s\(' % (leaf, name),
                                     f'{leaf}.{new_name}(', data)
            total += count
            data = newdata

        # Deal with files that import symbols individually
        imports = re.findall(r'from %s import (.*)\n' % module_name, data)
        for item in imports:
            #print('item', item)
            names = [n.strip() for n in item.split(',')]
            new_names = [conv.get(n) or n for n in names]
            #print('names', fname, names, new_names)
            new_line = 'from %s import %s\n' % (module_name,
                                                ', '.join(new_names))
            data = re.sub(r'from %s import (.*)\n' % module_name, new_line,
                          data)
            for name in names:
                new_name = conv.get(name)
                if new_name:
                    newdata, count = re.subn(r'\b%s\(' % name,
                                             f'{new_name}(', data)
                    data = newdata

        # Deal with mocks like:
        # unittest.mock.patch.object(module, 'Function', ...
        for name, new_name in conv.items():
            newdata, count = re.subn(r"%s, '%s'" % (leaf, name),
                                     f"{leaf}, '{new_name}'", data)
            total += count
            data = newdata

        if do_write and (total or imports):
            with open(fname, 'w', encoding='utf-8') as out:
                out.write(data)

    if commit:
        subprocess.call(['git', 'add', '-u'])
        msg = f'{prog}: Convert camel case in {os.path.basename(srcfile)}'
        msg += '\n\nConvert this file to snake case and update all files which use it.\n'
        subprocess.call(['git', 'commit', '-s', '-m', msg])


def main():
    """Main program"""
    epilog = 'Convert camel case function names to snake in a file and callers'
    parser = ArgumentParser(epilog=epilog)
    parser.add_argument('-c', '--commit', action='store_true',
                        help='Add a commit with the changes')
    parser.add_argument('-n', '--dry_run', action='store_true',
                        help='Dry run, do not write back to files')
    parser.add_argument('-s', '--srcfile', type=str, required=True, help='Filename to convert')
    args = parser.parse_args()
    process(args.srcfile, not args.dry_run, args.commit)

if __name__ == '__main__':
    main()
