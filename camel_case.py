
import re

def convert(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def convert_line(line):
    line = line.rstrip()
    if line and line[-1] == ';':
        words = line[:-1].split('\t')
        word = words[-1]
        if word != '}':
            pos = word.find('[')
            suffix = ''
            if pos != -1:
                suffix = word[pos:]
                word = word[:pos]
            word = convert(word)
            word = re.sub('__', '_', word)
            word = re.sub(' _', ' ', word)
            out = '%s\t%s%s;' % ('\t'.join(words[:-1]), word, suffix)
    else:
        out = line
    return out

def to_snake(name):
    """Convert a came-case name to snake case

    https://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case

    Args:
        name (str): Name to convert

    Returns:
        str: New name
    """
    leading_underscore = False
    if name[0] == '_':
        name = name[1:]
        leading_underscore = True
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
    if leading_underscore:
        name = '_' + name
    return name

if __name__ == "__main__":
    fname = '/home/sglass/asc'
    #'arch/x86/include/asm/arch-apollolake/fsp/fsp_s_upd.h'

    with open(fname) as inf:
        with open('asc', 'w') as outf:
            for line in inf:
                out = convert_line(line)
                print(line)
