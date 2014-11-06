"""

Created by: Nathan Starkweather
Created on: 11/03/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from http.server import HTTPServer, SimpleHTTPRequestHandler
from pysrc.snippets.metas import pfc_meta
from json import dumps

debug = 1
if debug:
    meta = pfc_meta
else:
    meta = type




class MyHTTPHandler(SimpleHTTPRequestHandler, metaclass=meta):

    def do_GET(self):
        call, params = self.parse_qs(self.path)
        print(params)
        try:
            handler = getattr(self, call)
            handler(**params)
        except:
            self.send_error(400, "Bad Path " + self.path)
            import traceback, sys
            tb = traceback.format_exc()
            print(tb, file=sys.stderr)
            return

    def parse_qs(self, qs):

        qs = qs.lstrip("/?")
        kvs = qs.split("&")
        if kvs[0] in {"/", "/?"}:
            kvs = kvs[1:]

        d = {}
        call = None
        for kv in kvs:
            k, v = kv.lower().split("=")
            if k == 'call':
                call = v
                continue
            if k in d:
                raise ValueError("Got multiple arguments for %s" % k)
            d[k] = v

        if call is None:
            raise ValueError("Bad Query String: No Call")

        return call, d


    def getmainvalues(self, json=True):
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
        self.send_response(200)
        self.send_header("Content-Length", len(mvs))
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(mvs)



class HelloServer(HTTPServer, metaclass=meta):
    """ A mock hello server that responds to calls.
    """
    def __init__(self, host='', port=12345):
        HTTPServer.__init__(self, (host, port), MyHTTPHandler)


def test1():
    s = HelloServer()
    import threading, time

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
    import sys
    try:
        test2()
    finally:
        sys.stdout.flush()
