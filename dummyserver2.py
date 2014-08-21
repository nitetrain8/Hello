"""

Created by: Nathan Starkweather
Created on: 08/19/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

import socket
from select import select



def recv_restful1(fp):

    """
    Receive a "RESTful" message using "HTTP protocol",
    where "RESTful" and "HTTP protocol" are limited implementations
    only useful for the dummy hello server

    @param fp: fp to read
    @type fp: file
    @return: bytearray
    @rtype: bytearray
    """
    buf = bytearray()

    # _readline = fp.readline
    # def readline():
    #     v = _readline()
    #     if v:
    #         print(v)
    #     return v
    # fp.readline = readline
    #
    # _read = fp.read
    # def read(n):
    #     v = _read(n)
    #     if v:
    #         print(v)
    #     return v
    # # fp.read = read

    # print("bleh")

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
            print("clength", clength)
        elif b'keep-alive' in line.lower():
            keep_alive = True

    # print(chunked)
    if chunked:
        print("parsing chunked")
        while True:
            line = fp.readline()
            buf.extend(line)
            size = int(line.strip(), 16)
            if size == 0:
                break
            line = fp.read(size + 2)
            buf.extend(line)
        buf.extend(fp.readline())
    elif clength:
        buf.extend(fp.read(clength))

    # fp.readline = _readline

    return keep_alive, buf


class Dummy():
    def __init__(self, dummy_addr, real_addr):
        self.dummy_addr = dummy_addr
        self.real_addr = real_addr

        s = socket.socket()
        s.bind(dummy_addr)
        s.listen(5)
        self.server_sock = s

    def mainloop(self):

        while True:
            dsock, addr = self.server_sock.accept()
            dfp = dsock.makefile('rwb')

            rsock = socket.socket()
            rsock.connect(self.real_addr)
            rfp = rsock.makefile('rbw')
            write_map = {rfp: dfp, dfp: rfp}
            to_write = {rfp: bytearray(), dfp: bytearray()}
            rfp.fileno = rsock.fileno
            dfp.fileno = dsock.fileno
            rfp.sock = rsock
            dfp.sock = dsock
            self.rsock = rsock
            self.dsock = dsock
            rsock.settimeout(3)
            dsock.settimeout(3)
            while True:
                fps = (rfp, dfp)
                rfps, wfps, xfps = select(fps, fps, (), 5)
                if not rfps and not wfps:
                    def closed(s): return getattr(s, '_closed', False)
                    print("Oh No!", closed(rsock), closed(dsock))
                    raise NameError("oh no")
                for fp in rfps:
                    # print("reading from", fp)
                    try:
                        print("reading")
                        keep_alive, buf = recv_restful1(fp)
                    except socket.timeout:
                        print(write_map[fp].sock.recv(4096))
                        raise

                    other_fp = write_map[fp]
                    to_write[other_fp].extend(buf)

                for fp in wfps:
                    # print("writing to", fp)
                    buf = to_write[fp]
                    if buf:
                        print("writing", len(buf), "bytes", end=' ')
                        fp.write(buf)
                        print("flushing buffer", end=' ')
                        fp.flush()
                        print("clearing buffer", end=' ')
                        buf.clear()  # mutates in place
                        print("done writing")

                if xfps:
                    print(*(s for s in xfps))




if __name__ == '__main__':
    daddr = ('', 12345)
    raddr = ('192.168.1.6', 80)

    from threading import Thread
    server = Dummy(daddr, raddr)

    def test():
        mthread = Thread(None, server.mainloop)

        def dummy():
            from urllib.request import Request, urlopen
            req = Request("http://192.168.1.5:12345/webservice/interface/?&call=getMainInfo")
            rsp = urlopen(req)
            print(rsp)

        # othread = Thread(None, dummy)

        mthread.start()
        # othread.start()

        import pdb

        pdb.set_trace()
    test()
    # server.mainloop()
