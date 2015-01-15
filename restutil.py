"""

Created by: Nathan Starkweather
Created on: 08/21/2014
Created in: PyCharm Community Edition

Misc utility functions for implementing quasi RESTful behavior
for dummy hello things.
"""
__author__ = 'Nathan Starkweather'


class BadError(Exception):
    """something bad happened"""
    pass


def parse_chunked_frominto(fp, buf):
    """
    @param fp: file
    @type fp: io.BufferedReader | io.BufferedRWPair
    @param buf: buf with exend method
    @type buf: bytearray | list
    @return: None
    @rtype: None
    """
    while True:
        line = fp.readline()
        buf.append(line)
        size = int(line.strip(), 16)
        if size == 0:
            buf.append(fp.readline())
            break
        line = fp.read(size + 2)
        buf.append(line)


def recv_restful(fp):

    """
    Receive a "RESTful" message using "HTTP protocol",
    where "RESTful" and "HTTP protocol" are limited implementations
    only useful for the dummy hello server

    @param fp: fp to read
    @type fp: io.BufferedReader | io.BufferedRWPair
    @return: bytearray
    @rtype: bytearray
    """
    buf = []

    call_line = fp.readline()
    buf.append(call_line)

    chunked = False
    clength = 0
    keep_alive = False
    while True:
        line = fp.readline()
        buf.append(line)
        if line == b'\r\n':
            break
        elif line.lower() == b'transfer-encoding: chunked\r\n':
            chunked = True
        elif b'content-length' in line.lower():
            clength = line.split(b': ', 1)[1]
            clength = int(clength, 10)

    if chunked and clength:
        raise BadError("chunked and clength")

    elif chunked:
        print("parsing chunked")
        parse_chunked_frominto(fp, buf)
        # print("parsed chunked")

    elif clength:
        print("parsing clength")
        chunk = fp.read(clength)
        if len(chunk) != clength:
            raise BadError("chunk != clength")
        buf.append(chunk)
        # print('parsed clength')
    return b''.join(buf)


def get_call(buf):
    nl = buf.find(b'\r\n')

    try:
        getline = buf[:nl]
        # get = getline.split(b' ')[1]
        return getline.split(b'=', 1)[1].split(b'&', 1)[0]
    except:
        return None


def getcall2(buf):
    nl = buf.find(b"\r\n")
    buf = buf[:nl]
    path = buf.split(b" ", 3)[1]
    qs = path.lstrip(b"/webservice/interface/")
    qs = qs.decode("utf-8")
    try:
        return qs, parse_qs(qs)
    except ValueError:
        return qs, (None, None)

from hello.mock.server import BadQueryString, MissingArgument


def parse_qs(qs, strict=False):
    """
    @rtype: (str, dict)
    """
    qs = qs.lstrip("/?&")
    kvs = qs.split("&")

    assert kvs[0] not in {"/", "/?"}
    # if kvs[0] in {"/", "/?"}:
    # kvs = kvs[1:]

    kws = {}
    for kv in kvs:
        k, v = kv.lower().split("=")
        if k in kws:
            if strict:
                raise BadQueryString("Got multiple arguments for %s" % k)
        kws[k] = v

    call = kws.pop('call', None)
    if call is None:
        raise ValueError("Call is None")

    try:
        del kws["_"]
    except KeyError:
        pass

    return call, kws
