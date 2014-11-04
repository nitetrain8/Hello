"""

Created by: Nathan Starkweather
Created on: 11/03/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from http.server import HTTPServer, SimpleHTTPRequestHandler
from pysrc.snippets.metas import pfc_meta
import socketserver

pfc_meta.wrap_cls(socketserver.BaseServer)
pfc_meta.wrap_cls(socketserver.TCPServer)
pfc_meta.wrap_cls(HTTPServer)


class HelloServer(HTTPServer, metaclass=pfc_meta):
    """ A mock hello server that responds to calls.
    """
    def __init__(self, host='', port=12345):
        HTTPServer.__init__(self, (host, port), SimpleHTTPRequestHandler)


if __name__ == '__main__':
    s = HelloServer()
    import threading, time
    t = threading.Thread(None, s.serve_forever)
    t.daemon = True
    t.start()
    time.sleep(1)

    from http.client import HTTPConnection
    c = HTTPConnection("", 12345)
    c.request("GET", "/")
    print(c.getresponse().read())
