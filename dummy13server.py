"""

Created by: Nathan Starkweather
Created on: 07/07/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from socket import socket, timeout as sock_timeout


def debug(*args, **kwargs):
    pass

# noinspection PyRedeclaration
debug = print


def getDummyMainValues():
    pass


def getDummyAdvValues():
    pass


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

    _readline = fp.readline
    def readline():
        v = _readline()
        if v:
            print(v)
        return v
    fp.readline = readline

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

    print(chunked)
    if chunked:
        print("parsing chunked", 74)
        while True:
            line = fp.readline()
            print("line is:", line)
            buf.extend(line)
            size = int(line.strip(), 16)
            if size == 0:
                break
            line = fp.read(size+2)
            buf.extend(line)
    elif clength:
        buf.extend(fp.read(clength))

    fp.readline = _readline

    return keep_alive, buf


def create_connection(host, port, timeout=3):
    addr = (host, port)
    attempts = 1
    while True:
        sock = socket()
        sock.settimeout(timeout)
        try:
            sock.connect(addr)
            return sock
        except sock_timeout:
            debug("Failed to connect to %s on port %d after %d attempts" % (host, port, attempts))
            attempts += 1


class DummyServer():
    """ Dummy server. Dummy_sock interacts with front-end (the world),
    Real_sock interacts with the back_sock.
    """
    def __init__(self, dummyhost, dummyport, realhost, realport):
        print("Initializing dummy server between %s:%d and %s:%d." %
              (dummyhost, dummyport, realhost, realport))
        self.dummyhost = dummyhost
        self.dummyport = dummyport
        self.realhost = realhost
        self.realport = realport

        self.server_sock = None
        self.back_sock = None
        self.front_sock = None

    def run(self):
        print("Creating Server Socket and beginning run.")
        running = True
        self.server_sock = socket()
        self.server_sock.bind((self.dummyhost, self.dummyport))
        # self.server_sock.settimeout(30)
        self.server_sock.listen(5)
        print("Running, beginning forwarding.")
        from select import select

        socks = [self.server_sock]
        sockmap = {self.server_sock: None}
        bufmap = {self.server_sock: None}
        while running:
            rlist, wlist, xlist = select(sockmap, sockmap, ())
            for sock in rlist:
                if sock is self.server_sock:
                    con, addr = sock.accept()
                    socks.append(con)
                    print("Got connection:", addr)
                    fw_sock = create_connection(self.realhost, self.realport)
                    sockmap[con] = fw_sock
                    sockmap[fw_sock] = con
                    bufmap[con] = None
                    bufmap[fw_sock] = None
                    continue

                buf = sock.recv(4096)
                bufmap[sockmap[sock]] = buf

            for sock in wlist:
                # print(sock)
                buf = bufmap[sock]
                if buf:
                    n = len(buf)
                    print("Forwarding message: from %r" % sock)
                    print(buf)
                    sock.sendall(buf)
                    if n == len(buf):
                        bufmap[sock] = None
                    else:
                        bufmap[sock] = buf[n:]
                        # print(bufmap[sock])

            for sock in xlist:
                print(sock)


    def begin_forwarding(self, from_sock, to_sock):

        keep_alive = False
        from_sock.settimeout(5)
        try:
            from_fp = from_sock.makefile('rb')
            to_fp = to_sock.makefile('rb')
            while True:
                keep_alive, msg_buf = recv_restful1(from_fp)
                # print("got from_fp")
                to_sock.sendall(msg_buf)
                keep_alive, rsp = recv_restful1(to_fp)
                # print("got to_fp")
                from_sock.sendall(rsp)

                if not keep_alive:
                    print("breaking connection...")
                    break
                else:
                    print("maintaining connection...")
            return True
        except Exception as e:
            raise
            return False


def main():

    from sys import argv

    # try:
    #     dummyhost, dummyport, realhost, realport = argv[1:]
    #     dummyport = int(dummyport)
    #     realport = int(realport)
    # except:
    #     print("Error\n", "Usage: python dummy13server.py <dummyhost> <dummyport> <realhost> <realport>", sep='')
    #     raise SystemExit

    dummyhost = '192.168.1.5'
    dummyport = 81
    realhost = '192.168.1.6'
    realport = 80

    server = DummyServer(dummyhost, dummyport, realhost, realport)
    server.run()


if __name__ == '__main__':
    main()
