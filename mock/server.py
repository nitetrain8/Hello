"""

Created by: Nathan Starkweather
Created on: 11/03/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from http.server import HTTPServer, SimpleHTTPRequestHandler
from hello.mock.state import HelloState
from pysrc.snippets.metas import pfc_meta
from json import dumps
import traceback
import sys

debug = 0
if debug:
    meta = pfc_meta
else:
    meta = type


class HelloServerException(Exception):
    pass

# Adding an explicit exception attribute makes
# it easier to extract a string representation
# of the error for returning to the client.


class BadQueryString(HelloServerException):
    def __init__(self, string):
        self.args = string,
        self.string = string


class UnrecognizedCommand(HelloServerException):
    def __init__(self, cmd):
        self.args = cmd,
        self.cmd = cmd
        self.err_code = "7815"


class MyHTTPHandler(SimpleHTTPRequestHandler, metaclass=meta):

    def do_GET(self):
        call, params = self.parse_qs(self.path)
        try:
            handler = getattr(self, call, None)
            if handler is None:
                raise UnrecognizedCommand(call)
            handler(params, True)
        except BadQueryString as e:
            self.send_error(400, "Bad query string:\"%s\"" % e.string)
        except Exception:
            self.send_error(400, "Bad Path " + self.path)
            tb = traceback.format_exc()
            print(tb, file=sys.stderr)
            return

    def parse_qs(self, qs):

        qs = qs.lstrip("/?&")
        kvs = qs.split("&")
        if kvs[0] in {"/", "/?"}:
            kvs = kvs[1:]

        kws = {}
        for kv in kvs:
            k, v = kv.lower().split("=")
            if k in kws:
                raise BadQueryString("Got multiple arguments for %s" % k)
            kws[k] = v

        call = kws.get('call')
        if call is None:
            raise BadQueryString("Bad Query String: No Call Specified.")

        return call, kws

    def send_good_reply(self, response, content_type='xml'):
        self.send_response(200)
        self.send_header("Content-Length", len(response))
        self.send_header("Content-Type", "application/" + content_type)
        self.end_headers()
        self.wfile.write(response)

    def getmainvalues(self, params, real_mode=False):
        """
        @param params: query string kv pairs
        @param real_mode: parse keywords the way the webserver does (True), or logically (False).
        @return:
        """

        if 'json' in params:
            del params['json']
            json = True
        else:
            json = False

        # debug
        json = True

        mv = {
            "result": "True",
            "message": {
                "agitation": {
                    "pv": 0.0000,
                    "sp": 20.000,
                    "man": 5.0000,
                    "mode": 2,
                    "error": 0,
                    "interlocked": 0
            },
                "temperature": {
                    "pv": 26.236,
                    "sp": 37.000,
                    "man": 45.000,
                    "mode": 2,
                    "error": 0,
                    "interlocked": 6
                },
                "do": {
                    "pv": -10.000,
                    "sp": 50.000,
                    "manUp": 500.00,
                    "manDown": 0.0000,
                    "mode": 2,
                    "error": 200
                },
                "ph": {
                    "pv": 11.594,
                    "sp": 7.0000,
                    "manUp": 0.0000,
                    "manDown": 7.0000,
                    "mode": 2,
                    "error": 100
                },
                "pressure": {
                    "pv": -7.8125E-10,
                    "mode": 0,
                    "error": 0
                },
                "level": {
                    "pv": 0.0000,
                    "mode": 0,
                    "error": 90
                },
                "condenser": {
                    "pv": 28.892,
                    "mode": 0,
                    "error": 90
                }
            }
        }

        mvs = dumps(mv).encode('ascii')
        self.send_good_reply(mvs, 'json')


class HelloServer(HTTPServer, metaclass=meta):
    """ A mock hello server that responds to calls.
    """
    def __init__(self, host='', port=12345, state=None):
        HTTPServer.__init__(self, (host, port), MyHTTPHandler)





def test1():
    s = HelloServer()
    import threading
    import time

    t = threading.Thread(None, s.handle_request)
    t.daemon = True
    print("Serving forever")
    t.start()
    time.sleep(1)
    from http.client import HTTPConnection

    c = HTTPConnection("localhost", 12345)
    print("Requesting")
    c.request("GET", "?&call=getMainValues&json=True")
    print("Getting response")
    print(c.getresponse().read())


def test2():
    s = HelloServer()
    s.handle_request()

if __name__ == '__main__':
    try:
        test1()
    finally:
        sys.stdout.flush()
