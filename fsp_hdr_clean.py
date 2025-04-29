#/usr/env/python

import os
import re
import sys

sys.path.append('tools/patman')

import command
import camel_case

def doit(fname):
    dirname = os.path.dirname(fname)
    with open(os.path.join(dirname, 'FspEas.h'), 'w'):
        pass
    out = command.Output('gcc', '-E', fname, '-I', dirname)
    for line in out.splitlines():
        if line and line[0] != '#':
            out = camel_case.convert_line(line)
            out2 = re.sub('uint(8|16|32)', r'u\1', out)
            if '{' not in out2 and '}' not in out2:
                words = out2.split('\t')
                out_words = []
                for word in words:
                    out_words.append(word.strip())
                last = out_words[-1]
                subwords = last.split(' ')
                if len(subwords) == 2:
                    typename, var = subwords
                    decl = '%s\t%s' % (typename, var)
                    out_words[-1] = decl
                out3 = '\t'.join(out_words)
            else:
                out3 = out2

            print(out3)

fname = '/scratch/sglass/intel_fsp/FSP/ApolloLakeFspBinPkg/Include/FspmUpd.h'
doit(fname)
