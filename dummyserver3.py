"""

Created by: Nathan Starkweather
Created on: 08/21/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

try:
    from .restutil import recv_restful, BadError, get_call
except (ImportError, SystemError):
    try:
        from restutil import recv_restful, BadError, get_call
    except (ImportError, SystemError):
        from hello.restutil import recv_restful, BadError, get_call

from socket import socket, timeout
from select import select


true_rsp = b'<?xml version="1.0" encoding="windows-1252" standalone="no" ?><Reply><Result>True</Result><Message>True</Message></Reply>'


class Dummy():
    def __init__(self, dummy, real):

        self.dummy_addr = dummy
        self.real_addr = real

        s = socket()
        s.bind(dummy)
        s.listen(5)
        self.server_sock = s

    def run(self):

        while True:
            dsock, addr = self.server_sock.accept()

            rsock = socket()
            rsock.connect(self.real_addr)
            try:
                self._forward(dsock, rsock)
            finally:
                rsock.close()
                dsock.close()

    def _forward(self, fromsock, tosock):

        dfp = fromsock.makefile('rwb')
        rfp = tosock.makefile('rbw')

        # to allow use of select
        rfp.fileno = tosock.fileno
        dfp.fileno = fromsock.fileno

        self.rsock = tosock
        self.dsock = fromsock

        write_map = {rfp: dfp, dfp: rfp}
        to_write = {rfp: bytearray(), dfp: bytearray()}
        fps = (rfp, dfp)

        def restful(fromfp, tofp, parse=lambda fbuf, tbuf: tbuf):
            fbuf = recv_restful(fromfp)
            tofp.write(fbuf)
            tofp.flush()

            tbuf = recv_restful(tofp)
            tbuf = parse(fbuf, tbuf)

            fromfp.write(tbuf)
            fromfp.flush()


        def parse_gmi(fbuf, tbuf):
            call = get_call(fbuf)
            print(call)
            if call == b'getMainInfo':
                print(tbuf)
                i = tbuf.find(b'\r\n\r\n')
                i += 4
                del tbuf[i:]
                tbuf.extend(("%x\r\n" % (len(true_rsp))).encode('ascii'))
                tbuf.extend(true_rsp)
                tbuf.extend(b'\r\n0\r\n\r\n')
                print(tbuf)
            return tbuf

        def parse_img(fbf, tbuf):
            thing = fbf.split(b' ', 2)[1]
            print(thing)
            thing = thing.lstrip(b'/dev/images/')
            if thing == b'png91.png':
                from time import sleep
                sleep(5)
            return tbuf

        while True:
            # print("Selecting")
            rlist, wlist, xlist = select(fps, fps, ())
            # if rlist and wlist:
            #     print("Selected")
            if xlist:
                print(xlist)
            # if not wlist:
            #     print("no rlist!")
            #     if not wlist:
            #         print("no wlist!")
            #         raise BadError("Possible deadlock")

            for fp in rlist:
                if fp is rfp:
                    if dfp not in wlist:
                        raise BadError("DFP not in wlist")
                    restful(rfp, dfp)
                elif fp is dfp:
                    if rfp not in wlist:
                        raise BadError("RFP not in wlist")
                    restful(dfp, rfp, parse_gmi)

            if self.rsock._closed:
                print("rsock closed")
            if self.dsock._closed:
                print("dsock closed")



def main():
    d = ('', 12345)
    r = ('192.168.1.6', 80)

    Dummy(d, r).run()

if __name__ == '__main__':
    main()
