"""

Created by: Nathan Starkweather
Created on: 05/28/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'


from socket import socket, timeout
from time import time
from xml.etree.ElementTree import parse


def reloadhello():
    import sys
    g = sys.modules['__main__'].__dict__
    for mod in ('hello', 'hello.hello'):
        try:
            del sys.modules[mod]
        except KeyError:
            pass
    exec("from hello.hello import *", g, g)


class HelloApp():
    def __init__(self, host='71.189.82.196', port=83, proto='HTTP/1.1', svcpth='webservice/interface/',
                 headers=None, timeout=5):
        self.host = host
        self.port = port
        self.proto = proto
        if not svcpth.endswith("/"):
            svcpth += "/"
        self.svcpth = svcpth
        self.timeout = timeout

        headers = headers or {}

        dflt_headers = {
            'Connection': 'keep-alive',
            'Accept': 'application/json',
            'User-Agent': 'Chrome/35.0.1916.114',
            'Accept-Encoding': 'ascii',
            'Accept-Language': 'en-US',
            'Host': ':'.join((host, str(port))),
        }

        dflt_headers.update(headers)

        self.headers = dflt_headers

        self.sock = self.connect((self.host, self.port), self.timeout, 3)
        self.fp = self.sock.makefile('rwb')

    def connect(self, addr, connection_timeout, attempts=3):
        """
        @param addr: address to connect (host, port)
        @type addr: (str, int)
        @param connection_timeout: timeout
        @type connection_timeout: int | float
        @return: socket
        @rtype: socket

        Addr is a tuple of (host, port) for consistency with the
        socket interface.

        """
        host, port = addr

        for attempt in range(attempts):
            s = socket()
            s.settimeout(connection_timeout)
            try:
                s.connect((host, port))
                return s
            except timeout:
                pass

        raise timeout("Failed to connect to (%s, %d) after %d attempts" % (host, port, attempts))

    def login(self, usr='user1', pwd=12345):

        args = [
            ('call', 'login'),
            ('skipValidate', 'True'),
            ('loader', 'Authenticating...'),
            ('val1', usr),
            ('val2', str(pwd))
        ]

        login_msg = self._build_msg(args)
        req, headers, body = self.communicate(login_msg)

        tree = parse(body)

        #: @type: xml.etree.ElementTree.Element
        root = tree.getroot()
        result = root.findtext('Result')

    def communicate(self, msg):

        fp = self.fp
        readline = fp.readline
        read = fp.read
        fp.write(msg)
        fp.flush()  # important!

        req = ''
        body = ''
        headers = {}
        msgbuf = bytearray()

        # request line
        req = readline().decode().strip()

        # headers
        while True:
            line = readline()
            line = line.rstrip(b'\r\n')

            if not line:
                break

            k, v = line.decode().split(": ", 1)
            headers[k] = v

        readline()  # clear empty post-header line

        # read the message body
        while True:
            line = readline().rstrip()

            if not line:
                break

            nbytes = int(line, 16)

            if nbytes == 0:
                readline()  # clear the final line in the buffer
                break

            chunk = read(nbytes)
            msgbuf.extend(chunk)

            # read terminating \r\n.
            readline()

        body = msgbuf.decode()

        return req, headers, body

    def _build_msg(self, args):

        if args[-1][0] != "_":
            args.append(("_", self._get_time()))

        argstr = '&'.join('='.join(arg) for arg in args)

        msg = "".join((
                    "GET ",  # method
                    self.svcpth,
                    "?&",
                    argstr,
                    " ",
                    self.proto,
                    "\r\n",
                    "\r\n".join(": ".join(item) for item in self.headers.items()),  # headers
                    "\r\n\r\n",  # first line break is the end of the final header
                                 # second line break is the 'empty line' at the end of headers
        ))

        return msg.encode('ascii')

    def _get_time(self):
        return '%.f' % (1000 * time())

    def __del__(self, *_):
        self.fp.close()
        self.sock.close()
