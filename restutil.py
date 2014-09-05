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
        buf.extend(line)
        size = int(line.strip(), 16)
        if size == 0:
            buf.extend(fp.readline())
            break
        line = fp.read(size + 2)
        buf.extend(line)


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
    buf = bytearray()

    call_line = fp.readline()
    buf.extend(call_line)

    chunked = False
    clength = 0
    keep_alive = False
    while True:
        line = fp.readline()
        buf.extend(line)
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
        # print("parsing chunked")
        parse_chunked_frominto(fp, buf)
        # print("parsed chunked")

    elif clength:
        # print("parsing clength")
        chunk = fp.read(clength)
        if len(chunk) != clength:
            raise BadError("chunk != clength")
        buf.extend(chunk)
        # print('parsed clength')
    return buf


def get_call(buf):
    nl = buf.find(b'\r\n')

    try:
        getline = buf[:nl]
        # get = getline.split(b' ')[1]
        return getline.split(b'=', 1)[1].split(b'&', 1)[0]
    except:
        return None
