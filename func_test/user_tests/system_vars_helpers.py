import re

def itersysvars(fname):
    with open(fname, 'r') as f:
        lines = f.read()
    lines = lines.splitlines()
    
    matcher = re.compile(r"<Name>(.*)<\/Name>")
    names = []
    for line in lines:
        m = matcher.match(line)
        if m is not None:
            names.append(m.group(1))
    
    for name in names:
        print(name)
        input()
    print("Done")
    
def isv_types(fname):
    with open(fname, 'r') as f:
        lines = f.read()
    lines = lines.splitlines()
    
    name_matcher = re.compile(r"<Name>(.*)<\/Name>")
    type_matcher = re.compile(r"<(.*)>")
    names = []
    for i, line in enumerate(lines):
        m = name_matcher.match(line)
        if m is not None:
            name = m.group(1)
            type = type_matcher.match(lines[i - 1]).group(1)
            names.append("%s: %.30s" % (name, type))
    
    for name in names:
        print(name)
        input()
    print("Done")