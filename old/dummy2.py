"""

Created by: Nathan Starkweather
Created on: 01/12/2015
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from http.server import HTTPServer
from http.client import HTTPConnection, BadStatusLine
from hello.mock.server import HelloHTTPHandler
import socket
from os.path import dirname, join, exists
from os import makedirs


def make_stdout_file(sock, mode, bufsize):
    f = sock.makefile(mode, bufsize)
    oldwrite = f.write
    def write(s):
        print(s)
        oldwrite(s)
    f.write = write
    return f


class MyHTTPConnection(HTTPConnection):
    def do_get_request(self, url, body=None, headers=None):
        headers = headers or {}
        return self._do_get_request(url, body, headers)

    def _do_get_request(self, url, body, headers):
        nattempts = 1
        retrycount = 32
        while True:
            try:
                self.request('GET', url, body, headers)
                rsp = self.getresponse()
            except (ConnectionAbortedError, BadStatusLine):
                if nattempts > retrycount:
                    raise
            except Exception:
                # debug. eventually all connection quirks should be worked out
                # and handled appropriately.
                import traceback
                print("=====================================")
                print("UNKNOWN ERROR OCCURRED DURING REQUEST")
                print("IPV4 ADDRESS:", self.host, self.port)
                print("REQUESTED URL: <%s>" % url)
                print("=====================================")
                print(traceback.format_exc())
                if nattempts > retrycount:
                    raise
            else:
                return rsp
            nattempts += 1
            self.reconnect()

    def reconnect(self):
        self.close()
        self.connect()


class MyHTTPHandler(HelloHTTPHandler):
    debug = False

    def __init__(self, request, client_address, server, to_con):
        """
        @param request: request
        @type request: socket.socket
        @param client_address: client address
        @type client_address: (str, str)
        @param server: server
        @type server: MyHTTPServer
        @param to_con: http connection to real webservice
        @type to_con: MyHTTPConnection
        @return:
        """
        self.to_con = to_con
        HelloHTTPHandler.__init__(self, request, client_address, server)

    def make_dummy(self, path, txt):

        try:
            # str?
            txt = txt.encode("utf-8", "strict")
        except AttributeError:
            # already bytes
            pass

        qs = self.parse_path(path)
        call, params = self.parse_qs(qs)
        if params:
            params.pop("_", None)
            params = sorted("%s-%s" % item for item in params.items())
            pstr = "_".join(params)
            sep = "_"
        else:
            pstr = ""
            sep = ""

        dummy_name = "".join((call, sep, pstr, ".dummy"))
        here = dirname(__file__)
        dummydir = join(here, "dummydata", "%s_%s" % (self.to_con.host, self.to_con.port))
        dummy_path = join(dummydir, dummy_name)

        if exists(dummy_path):
            return

        try:
            makedirs(dummydir)
        except FileExistsError:
            pass

        with open(dummy_path, 'wb') as f:
            f.write(txt)

    def setup(self):

        self.connection = self.request
        if self.timeout is not None:
            self.connection.settimeout(self.timeout)
        if self.disable_nagle_algorithm:
            self.connection.setsockopt(socket.IPPROTO_TCP,
                                       socket.TCP_NODELAY, True)
        if self.debug:
            self.rfile = make_stdout_file(self.connection, 'rb', self.rbufsize)
            self.wfile = make_stdout_file(self.connection, 'wb', self.wbufsize)
        else:
            self.rfile = self.connection.makefile('rb', self.rbufsize)
            self.wfile = self.connection.makefile('wb', self.wbufsize)

    def do_GET(self):
        rsp = self.to_con.do_get_request(self.path, None, self.headers)
        msg = rsp.read()

        self.make_dummy(self.path, msg)

        self.send_response_only(200, None)
        for key, value in rsp.headers.items():
            self.send_header(key, value)
        self.end_headers()

        if rsp.headers.get("transfer-encoding", "").lower() == 'chunked':
            chunked_msg = b''.join((hex(len(msg)).encode('ascii'), b'\r\n', msg, b'\r\n0\r\n\r\n'))
            self.wfile.write(chunked_msg)
            # self.wfile.write(hex(len(txt)).encode('ascii') + b"\r\n")
            # self.wfile.write(txt)
            # self.wfile.write(b"\r\n0\r\n\r\n")
        else:
            # todo- handle correctly
            # till then- write message and hope for the best
            self.log_message("Sending non-chunked transfer encoding!")
            self.wfile.write(msg)


class MyHTTPServer(HTTPServer):
    def __init__(self, from_addr='localhost:12345', to_addr='192.168.1.6:80', handler=MyHTTPHandler):
        if isinstance(from_addr, str):
            try:
                host, port = from_addr.split(":")
                port = int(port)
                from_addr = (host, port)
            except ValueError:
                from_addr = (from_addr, 80)
        HTTPServer.__init__(self, from_addr, handler)
        self.to_addr = to_addr
        self.to_con = MyHTTPConnection(to_addr)

    def finish_request(self, request, client_address):
        self.RequestHandlerClass(request, client_address, self, self.to_con)


def main():
    m = MyHTTPServer('localhost:12345', '192.168.1.82:80')
    MyHTTPHandler.debug = True
    m.serve_forever(0.01)


def spawn_server_thread(server):
    import threading
    t = threading.Thread(None, server.serve_forever)
    t.daemon = True
    t.start()
    return t


def server_with_getcall(to_addr='192.168.1.82:80'):
    from scripts.cli_data import getcall

    class HandlerWithGetcall(MyHTTPHandler):
        def do_GET(self):
            MyHTTPHandler.do_GET(self)

            qs = self.parse_path(self.path)
            call, params = self.parse_qs(qs)

            caller.getcall_ex_notext(call, True, **params)
            caller.getcall_ex_notext(call, False, **params)

    class HandlerServer(MyHTTPServer):
        def __init__(self):
            MyHTTPServer.__init__(self, to_addr=to_addr, handler=HandlerWithGetcall)

    server = HandlerServer()

    caller = getcall.CallGetter()
    server.caller = caller
    return server


if __name__ == '__main__':
    main()
