"""

Created by: Nathan Starkweather
Created on: 05/28/2014
Created in: PyCharm Community Edition

Module: test_module
Functions: test_functions

"""
import unittest
from os import makedirs
from os.path import dirname, join
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
from threading import Thread, Event
from select import select
from xml.etree.ElementTree import ElementTree, Element, SubElement
from io import BytesIO

TEST_HOST = gethostbyname(gethostname())
TEST_PORT = 12345
TEST_ADDR = (TEST_HOST, TEST_PORT)
TEST_TIMEOUT = 2


def dummy_http_msg(statusline, headers, body):
    """
    @param statusline: Status line Http:1/1 200 OK etc
    @type statusline: str
    @param headers: dict of headers
    @type headers: dict[str, str]
    @param body: response body
    @type body: bytes | bytearray

    build a dummy http message for testing.

    """

    response = bytearray()
    write = response.extend

    statusline = statusline.encode('ascii')
    write(statusline)
    write(b"\r\n")

    for k, v in headers.items():
        k = k.encode('ascii')
        v = v.encode('ascii')
        write(k)
        write(b": ")
        write(v)
        write(b"\r\n")

    write(b"\r\n")
    msg_end = b"\r\n"

    if headers.get('Transfer-Encoding') == 'chunked':
        msglen = "%x\r\n" % len(body)
        msglen = msglen.encode('ascii')
        write(msglen)
        msg_end = b"0\r\n\r\n"

    write(body)
    if not body.endswith(b'\r\n'):
        write(b'\r\n')

    write(msg_end)

    return response


class DummyServer():

    def __init__(self, host=TEST_HOST, port=TEST_PORT, timeout=TEST_TIMEOUT):

        sock = socket()
        sock.settimeout(timeout)
        sock.bind((host, port))
        sock.listen(5)
        self.sock = sock
        fileno = self.sock.fileno()

        # Each list is an integer mapping fileno to a corresponding object
        # Fileno to sock/file object mappings initialized to None,
        # buffers initialized to empty bytearrays.

        self.fd_sock = [None for _ in range(fileno + 1)]
        self.fd_rbuf = [bytearray() for _ in range(fileno + 1)]  # map fileno <-> read buffer
        self.fd_wbuf = [bytearray() for _ in range(fileno + 1)]  # map fileno <-> write buffer
        self.fd_sock[fileno] = self.sock
        self._maxfileno = fileno  # the maximum fd that will fit into the list without OOB error

        # To be set to true on clean exit
        self._clean_exit = False

        self.killevent = None
        self.mainthread = None

    def run(self):
        """
        Launch the server. The server runs in a separate thread.
        """
        mainthread = Thread(None, self.mainloop)
        self.mainthread = mainthread
        killevent = Event()
        self.killevent = killevent

        mainthread.daemon = True
        mainthread.start()

    def shutdown(self):
        self.killevent.set()

    def mainloop(self):
        """
        Main server loop. Build list of sockets to send to select(), using
        a short timeout
        """

        # unpack instance attributes for clarity (also LOAD_FAST vs GET_ATTR)
        # these are mutable, so their state *WILL* be modified
        # while the loop is running. by accessing via instance attr in other funcs

        server_sock = self.sock
        fd_sock = self.fd_sock
        fd_rbuf = self.fd_rbuf
        fd_wbuf = self.fd_wbuf
        parse_msg = self.parse_msg

        _zip = zip

        killflag_set = self.killevent.is_set

        while not killflag_set():
            # On windows, only sockets are supported in select() calls
            sel_r = [sock for sock in fd_sock if sock is not None]
            sel_w = [sock for sock, buf in _zip(fd_sock, fd_wbuf) if buf]

            # if not (sel_r or sel_w):
            #     _sleep(0.01)
            #     continue

            rlist, wlist, xlist = select(sel_r, sel_w, (), 0.01)

            for sock in rlist:
                fileno = sock.fileno()
                if sock is server_sock:
                    fileno = self.accept_connection()
                    self.fd_wbuf[fileno].extend(b"Thank you for connecting!\r\n\r\n")
                    continue
                msgbuf = self.fd_rbuf[fileno]
                msg = sock.recv(4096)
                msgbuf.extend(msg)

            for sock in wlist:
                fileno = sock.fileno()
                msgbuf = fd_wbuf[fileno]
                if msgbuf:
                    sock.sendall(msgbuf)
                    msgbuf.clear()

            for fileno, msgbuf in enumerate(fd_rbuf):
                if msgbuf:
                    msg = msgbuf.decode('utf-8')
                    print("MSG FROM %d:" % fileno, msg)
                    response = parse_msg(msg)
                    fd_wbuf[fileno].extend(response)
                    msgbuf.clear()

        # Mainloop terminated, clean up
        self._cleanup()

    def parse_msg(self, msg):
        """
        @param msg: str
        @type msg: str
        @return: response
        @rtype: bytes | bytearray
        """

        bad_response = b"HTTP:1/1 400 BAD REQUEST"

        msglines = msg.splitlines()
        try:
            method, url, proto = msglines[0].split()
        except ValueError:
            return bad_response

        if not url.startswith("webservice/interface/?&"):
            return bad_response

        call = url.lstrip("webservice/interface/?&")
        pairs = call.split("&")
        table = dict(item.split('=') for item in pairs)

        print("GOT HEADERS:")
        for k, v in table.items():
            print("%s = %r" % (k, v))

        root = Element("Reply")
        result = SubElement(root, "Result")
        result.text = "True"
        message = SubElement(root, "Message")
        message.text = "Thanks for connecting!"

        file = BytesIO()
        tree = ElementTree(root)
        tree.write(file, 'us-ascii', True, None, 'xml', short_empty_elements=False)

        status = "HTTP:1/1 200 OK"
        headers = {
            'Transfer-Encoding': 'chunked',

        }
        body = file.getbuffer()

        response = dummy_http_msg(status, headers, body)
        return response



    def accept_connection(self):
        """
        Accept incoming connection to the server. Open connection, make a buffered reader,
        update fd lists as necessary.

        """
        con, addr = self.sock.accept()
        fileno = con.fileno()

        # If the fileno is greater than the biggest index in the list, grow the list.
        if fileno > self._maxfileno:
            n = fileno - self._maxfileno + 1
            self.fd_sock.extend(None for _ in range(n))
            self.fd_rbuf.extend(bytearray() for _ in range(n))
            self.fd_wbuf.extend(bytearray() for _ in range(n))
            self._maxfileno = fileno

        self.fd_sock[fileno] = con

        return fileno

    def _cleanup(self):
        """
        @return:
        @rtype:
        """
        errors = []

        fd_sock = self.fd_sock

        for fileno, sock in enumerate(fd_sock):
            if sock is not None:
                try:
                    sock.close()
                    fd_sock[fileno] = None
                except Exception as e:
                    errors.append((sock, e))

        if errors:
            print("%d Errors" % len(errors))
            for fp, error in errors:
                print("Error shutting down resource:", fp)
                print(error)

        self._clean_exit = all(sock is None for sock in fd_sock)

        if not self._clean_exit:
            print(self.fd_sock)

    def __del__(self):
        self._cleanup()
        if not self._clean_exit:
            print("Warning, leaked resources:")
            print(*(sock for sock in self.fd_sock if sock is not None), sep="\n")


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
