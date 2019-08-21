# Insert a header #include into all files that have a particular function call
# in them

from __future__ import print_function

import os
import re
import sys

sys.path.append('/home/sjg/u/tools/patman')

import command


def process_file(fname, func, insert_hdr):
    if fname[-2:] not in ('.c'):
        return
    with open(fname, 'r') as fd:
        data = fd.read()
    if func not in data:
        return
    to_add = '#include <%s>' % insert_hdr
    if to_add in data:
        return
    lines = data.splitlines()
    out = []
    done = False
    found_includes = False
    for line in lines:
        if not done:
            if line.startswith('#include'):
                m = re.match('#include <(.*)>', line)
                if m:
                    hdr = m.group(1)
                    if hdr != 'common.h':
                        if insert_hdr < hdr or hdr.startswith('linux'):
                            out.append(to_add)
                            done = True
                found_includes = True
            elif found_includes:
                out.append(to_add)
                done = True
        out.append(line)
    with open(fname, 'w') as fd:
        for line in out:
            print(line, file=fd)


def doit(func, insert_hdr):
    fnames = command.Output('git', 'grep', '-l', func).splitlines()
    for fname in fnames:
        if os.path.islink(fname):
            continue
        process_file(fname, func, insert_hdr)

#all = 'ENV_VALID,ENV_INVALID,ENV_REDUND'.split(',')
#all = 'env_op_create,env_op_delete,env_op_overwrite'.split(',')
#for item in all:
	#doit(item, 'search.h')

#all = 'U_BOOT_ENV_CALLBACK'.split(',')
#for item in all:
	#doit(item, 'env_callback.h')

#all = 'ENV_INVALID,ENV_INVALID,ENV_REDUND'.split(',')
#for item in all:
	#doit(item, 'env.h')

#all = 'CONFIG_ENV_SIZE,CONFIG_ENV_SECT_SIZE,ENV_OFFSET,CONFIG_ENV_ADDR'.split(',')
#all += 'ENV_IS_EMBEDDED,CONFIG_SYS_REDUNDAND_ENVIRONMENT,CONFIG_ENV_OFFSET'.split(',')
#all += 'CONFIG_SYS_REDUNDAND_ENVIRONMENT,ENV_HEADER_SIZE'.split(',')
#for item in all:
	#doit(item, 'environment.h')

#all = 'H_NOCLEAR,H_FORCE,H_INTERACTIVE,H_HIDE_DOT,H_MATCH_KEY,H_MATCH_DATA'
#all += ',H_MATCH_BOTH,H_MATCH_IDENT,H_MATCH_SUBSTR,H_MATCH_REGEX,H_MATCH_METHOD'
#all += ',H_PROGRAMMATIC,H_ORIGIN_FLAGS'
#for item in all.split(','):
	#doit(item, 'environment.h')

#all = 'ENVL_,ENV_CALLBACK_LIST_STATIC'
#for item in all.split(','):
	#doit(item, 'environment.h')
