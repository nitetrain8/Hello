"""

Created by: Nathan Starkweather
Created on: 05/28/2014
Created in: PyCharm Community Edition

Module: test_module
Functions: test_functions

"""
import unittest
from os import makedirs
from os.path import dirname, join, exists
from shutil import rmtree


__author__ = 'PBS Biotech'

curdir = dirname(__file__)
test_dir = dirname(curdir)
test_temp_dir = join(test_dir, "temp")
temp_dir = join(test_temp_dir, "temp_dir_path")
test_input = join(curdir, "test_input")


def setUpModule():
    try:
        makedirs(temp_dir)
    except FileExistsError:
        pass


def tearDownModule():
    try:
        rmtree(temp_dir)
    except FileNotFoundError:
        pass

try:
    from hello import HelloApp
except ImportError:
    from hello.hello import HelloApp

from socket import socket, gethostbyname, gethostname

# These are necessary for setting up a dummy server implementation
from queue import Queue
from threading import Thread
from select import select
from os import kill
from signal import signal, SIGINT


TEST_HOST = "localhost"
TEST_PORT = 12345
TEST_TIMEOUT = 2


class DummyServer():
    def __init__(self, host=TEST_HOST, port=TEST_PORT, timeout=TEST_TIMEOUT):
        sock = socket()
        sock.settimeout(timeout)
        sock.bind((host, port))
        sock.listen(5)
        self.sock = sock
        self.fp = self.sock.makefile('rwb')

        fileno = self.fp.fileno()

        self.sock_fo = [None for _ in range(fileno + 1)]
        self.fd_fo = [None for _ in range(fileno + 1)]  # map fileno <-> file object
        self.fd_r = [bytearray() for _ in range(fileno + 1)]  # map fileno <-> read buffer
        self.fd_w = [bytearray() for _ in range(fileno + 1)]  # map fileno <-> write buffer
        self.sock_fo[fileno] = self.sock
        self.fd_fo[fileno] = self.fp
        self._maxfileno = fileno  # the maximum fd that will fit into the list without OOB error

        # To be set to true on clean exit
        self._clean_exit = False

    def run(self):
        """
        Launch the server. The server runs in a separate thread.
        """
        sthread = Thread(None, self.mainloop)

    def SIGINT_handler(self, sig, frame):
        rv = self._cleanup()
        if rv:
            self._clean_exit = True
        raise SystemExit()

    def mainloop(self):

        signal(SIGINT, self.SIGINT_handler)

        server_fp = self.fp.fileno()
        _select = select

        while True:
            sel_r = [fileno for fileno, buf in enumerate(self.fd_r) if buf is not None]
            sel_w = [fileno for fileno, buf in enumerate(self.fd_w) if buf is not None]

            rlist, wlist, xlist = _select(sel_r, sel_w, ())

            for fileno in rlist:
                fp = self.fd_fo[fileno]

                if fp is server_fp:
                    fileno = self.accept_connection()
                    self.fd_w[fileno].extend(b"Thank you for connecting!\r\n")
                    continue

                msg = fp.read()
                self.fd_r[fileno].extend(msg)

            for fileno in wlist:

                fp = self.fd_fo[fileno]
                msg = self.fd_w[fileno]
                fp.write(msg)
                fp.flush()
                self.fd_w[fileno].clear()



    def accept_connection(self):
        """
        Accept incoming connection to the server. Open connection, make a buffered reader,
        update fd lists as necessary.

        """
        con, addr = self.sock.accept()
        fp = con.makefile('rwb')
        fileno = fp.fileno()

        # If the fileno is greater than the biggest index in the list, grow the list.
        if fileno > self._maxfileno:
            n = fileno - self._maxfileno + 1
            self.fd_fo.extend(None for _ in range(n))
            self.sock_fo.extend(None for _ in range(n))
            self.fd_r.extend(None for _ in range(n))
            self.fd_w.extend(None for _ in range(n))
            self._maxfileno = fileno

        self.fd_fo[fileno] = fp
        self.sock_fo[fileno] = con

        return fileno

    def _cleanup(self):
        """
        @return:
        @rtype:
        """
        errors = []

        fd_fo = self.fd_fo

        while fd_fo:
            fp = fd_fo.pop()
            if fp is not None:
                try:
                    fp.close()
                except Exception as e:
                    errors.append((fp, e))

        sock_fo = self.sock_fo

        while sock_fo:
            sock = sock_fo.pop()
            if sock is not None:
                try:
                    sock.close()
                except Exception as e:
                    errors.append((sock, e))

        if errors:
            print("%d Errors" % len(errors))
            for fp, error in errors:
                print("Error shutting down resource:", fp)
                print(error)
            return False
        return True

    def __del__(self):
        self._cleanup()
        if not self._clean_exit:
            print("Warning, leaked resources:")
            print(*(fp for fp in self.fd_fo if fp is not None), sep='\n')
            print(*(sock for sock in self.sock_fo if sock is not None), sep="\n")
        self._cleanup()






# noinspection PyProtectedMember
class TestHello(unittest.TestCase):

    def test_build_call(self):
        """
        @return: None
        @rtype: None
        """

        app = HelloApp()

        args = [
            ("foo", "bar"),
            ("baz", "fizz"),
            ("buzz", "12"),
            ("_", "1")
        ]

        msg = app._build_call(args).decode('utf-8')

        lines = msg.splitlines(False)

        # check the request line
        exp_req_line = "GET webservice/interface/?&foo=bar&baz=fizz&buzz=12&_=1 HTTP/1.1"
        result_req_line = lines[0]
        self.assertEqual(exp_req_line, result_req_line)

        # ensure message is properly terminated- Last four chars should be '\r\n\r\n'
        self.assertEqual(msg[-4:], '\r\n\r\n')

        # ensure all headers are here.
        result_headers = set(tuple(item.split(": ", 1)) for item in lines[1:-1])
        for header in app.headers.items():
            self.assertIn(header, result_headers)

        app.sock.close()
        app.fp.close()

    def test_communciate(self):
        """
        Test communicate. Yay.
        """
        server = socket()
        host = gethostbyname(gethostname())
        port = 12345

        server.bind((host, port))
        server.listen(1)
        server.settimeout(5)

        # socket.accept is blocking but socket.connect is not.
        # Set up the hello connection first, then accept.
        app = HelloApp(host, port)
        con, addr = server.accept()
        confp = con.makefile('rwb')

        args = [
            ("foo", "bar"),
            ("baz", "fizz"),
            ("buzz", "12"),
            ("_", "1")
        ]

        msg = app._build_call(args)
        n = len(msg)

        queue = Queue()

        # launch this server process in a separate thread to avoid deadlock

        def test_get_msg(fp, n, q):
            result = fp.read(n)
            print("RESULT GOT:", result)
            q.put(result)
            fp.write(b"REQ_LINE\r\nHEADER: VALUE\r\n\r\n0\r\n\r\n")
            fp.flush()

        # Possible w/o threads?

        sthread = Thread(None, test_get_msg, None, (confp, n, queue))
        sthread.start()
        req, headers, body = app.communicate(msg)
        sthread.join()
        msg_read = queue.get()

        self.assertEqual(req, "REQ_LINE")
        self.assertEqual(headers, {"HEADER": "VALUE"})
        self.assertEqual(body, '')
        self.assertEqual(msg_read, msg)

        con.close()
        confp.close()
        app.sock.close()
        app.fp.close()
        server.close()


if __name__ == '__main__':
    unittest.main()
