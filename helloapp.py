"""

Created by: Nathan Starkweather
Created on: 05/28/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

import shutil
from socket import socket, timeout
from time import time
from xml.etree.ElementTree import parse as xml_parse
from io import BytesIO, StringIO


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
    def __init__(self, host='71.189.82.196', port=83, proto='HTTP/1.1', svcpth='/webservice/interface/',
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
            except:
                print("Failed after %d attempts" % attempts)
                raise

        raise timeout("Failed to connect to (%s, %d) after %d attempts" % (host, port, attempts))

    def login(self, usr='user1', pwd=12345):

        args = [
            ('call', 'login'),
            ('skipValidate', 'True'),
            ('loader', 'Authenticating...'),
            ('val1', usr),
            ('val2', str(pwd))
        ]

        login_msg = self._build_call(args)
        req, headers, body = self.communicate(login_msg)

        tree = xml_parse(body)

        #: @type: xml.etree.ElementTree.Element
        root = tree.getroot()
        result = root.findtext('Result')

        # Never use eval!
        if result == "True":
            return True
        else:
            return False

    def communicate(self, msg):

        fp = self.fp
        readline = fp.readline
        read = fp.read
        fp.write(msg)
        fp.flush()  # important!

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

        if 'chunked' in headers.get('Transfer-Encoding', ''):

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

        elif 'Content-Length' in headers:
            nbytes = int(headers['Content-Length'])
            chunk = read(nbytes)
            msgbuf.extend(chunk)

        else:

            # Hopefully this doesn't block....
            while True:
                line = readline().strip()
                if not line:
                    break
                msgbuf.extend(line)

        body = msgbuf.decode('utf-8')

        return req, headers, body

    def getUsers(self):

        args = [
            ('call', 'getUsers'),
        ]
        call = self._build_call(args)
        result = self.communicate(call)
        req, headers, body = result
        try:
            file = StringIO(body)
            tree = xml_parse(file)
            root = tree.getroot()
            msg = root.find("Message")
        except:
            print(result)
            raise
        return msg.text

    def _build_call(self, args):
        """
        @param args: list of key, value tuples relevant for the call
        @type args: list[(str, str)]
        @return: byte string representing full HTTP message for a call
        @rtype: bytes

        Build the full HTTP message to be sent to the server. Returns
        message encoded in ascii.

        """

        # Todo- pre-encode fragments instead of building string as unicode?

        # Ensure that the timestamp is present.
        if args[-1][0] != "_":
            args.append(("_", self._get_time()))

        argstr = '&'.join('='.join(arg) for arg in args)

        msg = "".join((
                    "GET ",  # method
                    self.svcpth,  # url to interface method
                    "?&",
                    argstr,  # &key1=val1&key2=val2....
                    " ",
                    self.proto,  # HTTP:1/1 etc
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

    def getMainValues(self):

        args = [
            ('call', 'getMainValues'),
            ('json', 'true')
        ]

        msg = self._build_call(args)
        req, headers, body = self.communicate(msg)
        print(body)

    def getConfig(self):

        args = [
            ('call', 'getConfig')
        ]

        call = self._build_call(args)
        req, headers, response = self.communicate(call)
        file = StringIO(response)
        tree = xml_parse(file)
        root = tree.getroot()
        msg = root.find('Message')
        cluster = msg.find('Cluster')

        types = {
            'DBL': float,
            'I32': int,
            'U8': int,
            'U16': int,
            'EW': lambda x: x  # Identity function, see "EW" in if statement below
        }

        citer = cluster.iter('Cluster')
        next(citer)  # cluster element
        # next(citer)  # name ("System Variables")
        # next(citer)  # Number of elements ("13")

        bigdata = {}
        for elem in citer:
            cluster = elem.iter()

            next(cluster)  # cluster element
            category = next(cluster).tag
            elements = int(next(cluster).tag)

            data = {}

            while True:
                try:
                    tag_type = next(cluster).tag  # type tag
                except StopIteration:
                    break

                name = next(cluster).text

                if tag_type == 'EW':
                    choices = []
                    while True:
                        choice = next(cluster)
                        if choice.tag == 'Val':
                            val = choice.text
                            break
                        else:
                            choices.append(choice.text)
                    val = choices[int(val)]
                else:
                    val = next(cluster).text

                    # Map tag type to python type. For "EW", handle logic
                    # above and pass through identity function.
                data[name] = types[tag_type](val)

            bigdata[category] = data

        return bigdata