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
    call_line = fp.readline()





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
        self.dummyhost = dummyhost
        self.dummyport = dummyport
        self.realhost = realhost
        self.realport = realport

        self.server_sock = None
        self.back_sock = None
        self.front_sock = None

    def run(self):

        running = True
        while running:

            self.server_sock = socket()
            self.server_sock.bind(self.dummyhost, self.dummyport)
            self.back_sock = create_connection(self.realhost, self.realport)
            self.front_sock = self.server_sock.accept()

            running = self.begin_forwarding(self.front_sock, self.back_sock)

            self.back_sock.close()
            self.front_sock.close()

    def begin_forwarding(self, from_sock, to_sock):

        try:
            from_fp = from_sock.makefile('rb')
            msg_buf, call = recv_restful1(from_fp)
            call_line = msg_buf[:msg_buf.find(b'\r\n')]
            call = call_line.split(b"?&call=", 1)[1].split(b"&", 1)[0]
            if call == b'getMainValues':
                rsp_buf = getDummyMainValues()
            elif call == b'getAdvancedValues':
                rsp_buf = getDummyAdvValues()

            return True
        except:
            return False


def main():

    from sys import argv

    try:
        dummyhost, dummyport, realhost, realport = argv[1:]
        dummyport = int(dummyport)
        realport = int(realport)
    except:
        print("Error\n", "Usage: python dummy13server.py <dummyhost> <dummyport> <realhost> <realport>", sep='')
        raise SystemExit

    server = DummyServer(dummyhost, dummyport, realhost, realport)
    server.run()


if __name__ == '__main__':
    main()
