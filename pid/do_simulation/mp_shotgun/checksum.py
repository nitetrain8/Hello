import hashlib
def checksum(l):
    s = "\n".join("%s.%s.%s.%s"%a for a in l)
    s = s.encode('ascii')
    h = hashlib.md5(s).digest()
    cs = b"md5:"+b":".join(map(b"%.2x".__mod__, h))
    return cs.decode('utf-8')