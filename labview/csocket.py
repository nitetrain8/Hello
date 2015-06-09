"""

Created by: Nathan Starkweather
Created on: 03/17/2015
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'


import socket
from select import select
from hello.logger import BuiltinLogger
from time import sleep


class ReverseEchoServer():
    def __init__(self, ip='', port=12345):
        self.logger = BuiltinLogger(self.__class__.__name__)
        self.sock = self.init_sock()
        self.ip = ip
        self.port = port

    def init_sock(self):
        self.logger.debug("Initializing Socket")
        return socket.socket()

    def run(self):
        if self.sock is None:
            self.sock = self.init_sock()
        self.logger.debug("Binding to %s:%s" % (self.ip, self.port))
        self.sock.bind((self.ip, self.port))
        self.logger.debug("Listening to 1 connection(s)")
        self.sock.listen(1)
        try:
            self.logger.debug("Beginning mainloop")
            self.mainloop(self.sock)
        except KeyboardInterrupt:
            self.logger.debug("Got keyboard interrupt, exiting cleanly")
        finally:
            self.logger.debug("Shutting down server socket")
            self.sock.shutdown()
            self.sock.close()
            self.sock = None

    def mainloop(self, sock):
        msg = b'Hello World'
        while True:
            self.logger.debug("Accepting connection")
            con, addr = sock.accept()
            self.logger.debug("Selecting read list")
            rlist, wlist, xlist = select([con], [], [], 0.1)
            if con in rlist:
                self.logger.debug("Reading from connection")
                msg = con.recv(4096)
            rlist, wlist, xlist = select([], [con], [], 0.1)
            if con in wlist:
                print(msg)
                tosend = msg[::-2]
                self.logger.debug("Writing to connection: '%s'" % tosend)
                sent = con.send(tosend)
                self.logger.debug("Sent %d of %d bytes" % (sent, len(tosend)))
                sleep(5)
                con.shutdown(socket.SHUT_RDWR)
                con.close()


class simpleproxy():
    def __init__(self, from_addr, to_addr):
        self.from_addr = from_addr
        self.to_addr = to_addr

    def mainloop(self):
        ssock = socket.socket()
        ssock.bind(self.from_addr)
        ssock.listen(5)

        fsock, _ = ssock.accept()

        tsock = socket.socket()
        tsock.connect(self.to_addr)

        forwards = {fsock: tsock,
                    tsock: fsock}

        bufs = {fsock: b'',
                tsock: b''}

        socks = fsock, tsock, ssock

        while True:
            rs, ws, xs = select(socks, socks, [], 0.1)
            for s in rs:
                if s is ssock:
                    con, addr = ssock.accept()
                    con2 = socket.socket()
                    con2.connect(self.to_addr)
                    forwards[con] = con2
                    forwards[con2] = con
                    bufs[con] = b''
                    bufs[con2] = b''
                else:
                    other = forwards[s]
                    rsp = s.recv(4096)
                    if rsp:
                        bufs[other] += rsp
                    if rsp:
                        i = 0
                        assert isinstance(rsp, bytes)
                        for i, c in enumerate(rsp):
                            if c > 127:
                                break
                        printable = rsp[:i]
                        other = rsp[i:]
                        if printable:
                            print(printable.decode('utf-8'))
                        if other:
                            print(other)


            for s in ws:
                if s is ssock:
                    continue
                if bufs[s]:
                    l = len(bufs[s])
                    n = s.send(bufs[s])
                    if n < l:
                        bufs[s] = bufs[s][:n]
                    else:
                        bufs[s] = b''


class simpleproxy2(simpleproxy):
    def mainloop(self):
        ssock = socket.socket()
        ssock.bind(self.from_addr)
        ssock.listen(5)

        fsock, _ = ssock.accept()

        tsock = socket.socket()
        tsock.connect(self.to_addr)

        forwards = {fsock: tsock,
                    tsock: fsock}

        bufs = {fsock: b'',
                tsock: b''}

        socks = fsock, tsock
        while True:
            rl, wl, xl = select(socks, socks, [], 0.1)
            for s in rl:
                t = forwards[s]
                msg = s.recv(4096)
                bufs[t] += msg
                print(msg)

            for s in wl:
                if bufs[s]:
                    l = len(bufs[s])
                    n = s.send(bufs[s])
                    if n < l:
                        bufs[s] = bufs[s][:n]
                    else:
                        bufs[s] = b''

def main():
    ReverseEchoServer().run()


def main2():
    fromaddr = ('localhost', 12345)
    toaddr = ('localhost', 7681)
    p = simpleproxy(fromaddr, toaddr)
    p.mainloop()

def main3():
    fromaddr = ('localhost', 12345)
    toaddr = ('localhost', 7681)
    p = simpleproxy2(fromaddr, toaddr)
    p.mainloop()

if __name__ == '__main__':
    main2()
