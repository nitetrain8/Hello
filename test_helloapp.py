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
from queue import Queue
from threading import Thread


# noinspection PyProtectedMember
class TestHello(unittest.TestCase):

    def test_build_call(self):
        """
        @return: None
        @rtype: None
        """

        app = HelloApp()

        args = (
            ("foo", "bar"),
            ("baz", "fizz"),
            ("buzz", "12"),
            ("_", "1")
        )

        msg = app._build_msg(args).decode('utf-8')

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

        args = (
            ("foo", "bar"),
            ("baz", "fizz"),
            ("buzz", "12"),
            ("_", "1")
        )

        msg = app._build_msg(args)
        n = len(msg)

        queue = Queue()

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
