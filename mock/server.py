"""

Created by: Nathan Starkweather
Created on: 11/03/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from http.server import HTTPServer, SimpleHTTPRequestHandler
from hello.mock.state import HelloState
from pysrc.snippets.metas import pfc_meta
from xml.etree.ElementTree import Element, SubElement, tostring as xml_tostring
from json import dumps as json_dumps
import traceback
import inspect
import sys

debug = 0
if debug:
    meta = pfc_meta
else:
    meta = type


def arbitrary_stack_trace(backup=1):

    """
    Modified from http://mahmoudimus.com/blog/2011/02/arbitrary-stack-trace-in-python/
    """

    # get the currently frames' stack
    # this returns the frameobject, the filename,
    # the line number of the current line, the
    # function name, a list of lines of context from
    # the source code, and the index of the current
    # line within that list.

    stack = inspect.stack()

    # reverse the stack trace so the most recent is at the bottom of the stack

    stack.reverse()
    stack = stack[backup:]
    stack_list = []

    try:
        for s in stack:
            _, filename, line_no, func_name, code_list, index_in_code_list = s
            stack_list.append(
                (filename, line_no, func_name, code_list[index_in_code_list])
            )
        rv = ''.join(traceback.format_list(stack_list))
    finally:
        # avoid memory leak issues
        del stack
    return rv


class HelloServerException(Exception):
    pass

# Adding an explicit exception attribute makes
# it easier to extract a string representation
# of the error for returning to the client.


class BadQueryString(HelloServerException):
    """ Couldn't parse query string, multiple arguments given,
    or other syntax & semantic errors.
    """
    def __init__(self, string):
        self.args = string,
        self.string = string


class UnrecognizedCommand(HelloServerException):
    """ User asked for something weird.
    """
    def json_reply(self):
        reply = {
            'result': self.result,
            "message": self.message
        }
        reply = json_dumps(reply)
        return reply

    def xml_reply(self):
        reply = Element("Reply")
        result = SubElement(reply, "Result")
        result.text = self.result
        message = SubElement(reply, "Message")
        message.text = self.message
        reply = xml_tostring(reply, 'us-ascii')
        return reply

    def __init__(self, cmd, rsp_fmt="xml"):
        self.args = cmd,
        self.cmd = cmd
        self.err_code = 7815
        self.result = "False"
        self.message = "Unrecognized Command: %s" % self.err_code
        self.rsp_fmt = rsp_fmt

        if rsp_fmt == 'json':
            self.reply = self.json_reply()
        else:
            self.reply = self.xml_reply()


class ArgumentError(UnrecognizedCommand):
    """ User asked for something known, but with bad arguments.
    """
    def __init__(self, what, err_code, rsp_fmt, msg=None):
        self.result = "False"
        self.what = what
        if msg:
            self.message = msg
        else:
            self.message = "Unrecognized %s: %s" % (what, err_code)
        self.args = self.message,
        self.err_code = err_code
        self.rsp_fmt = rsp_fmt

        if rsp_fmt == 'json':
            self.reply = self.json_reply()
        else:
            self.reply = self.xml_reply()


class UnexpectedArgument(UnrecognizedCommand):
    def __init__(self, what, err_code, rsp_fmt):
        self.result = "False"
        self.what = what
        self.message = "Unexpected Argument(s) %s: %s" % (what, err_code)
        self.args = self.message,
        self.err_code = err_code
        self.rsp_fmt = rsp_fmt

        if rsp_fmt == 'json':
            self.reply = self.json_reply()
        else:
            self.reply = self.xml_reply()


class UnknownInternalError(UnrecognizedCommand):
    def __init__(self):
        self.result = "False"
        self.what = "Unknown Error"
        self.message = ""
        self.args = self.message,
        self.err_code = -1
        self.rsp_fmt = 'json'
        self.reply = self.json_reply()


class MyHTTPHandler(SimpleHTTPRequestHandler, metaclass=meta):

    json_true_response = json_dumps(
        {'result': "True",
         "message": "True"}
    ).encode('ascii')

    xml_true_response = '<?xml version="1.0" encoding="us-ascii" standalone="no" ?>' \
                        '<Reply><Result>True</Result><Message>True</Message></Reply>'
    xml_true_response = xml_true_response.encode('us-ascii')

    def do_GET(self):
        try:
            call, params = self.parse_qs(self.path)
            handler = getattr(self, call, None)
            if handler is None:
                raise UnrecognizedCommand(call)
            handler(params, True)
        except BadQueryString as e:
            self.send_error(400, "Bad query string: \"%s\"" % e.string)
        except ArgumentError as e:
            self.send_reply(e.reply, e.rsp_fmt)
        except UnrecognizedCommand as e:
            self.send_reply(e.reply, e.rsp_fmt)
        except Exception:
            self.send_error(400, "Bad Path " + self.path)
            tb = traceback.format_exc()
            print(tb, file=sys.stderr)
        finally:
            self.wfile.flush()

    def parse_qs(self, qs, strict=False):

        qs = qs.lstrip("/?&")
        kvs = qs.split("&")
        if kvs[0] in {"/", "/?"}:
            kvs = kvs[1:]

        kws = {}
        for kv in kvs:
            k, v = kv.lower().split("=")
            if k in kws:
                if strict:
                    raise BadQueryString("Got multiple arguments for %s" % k)
            kws[k] = v

        call = kws.get('call')
        if call is None:
            raise ArgumentError("Syntax", 7816, 'json' if 'json' in kws else 'xml', "Syntax Error 7816")

        return call, kws

    def send_reply(self, body, content_type='xml'):
        self.send_response(200)
        self.send_header("Content-Length", len(body))
        self.send_header("Content-Type", "application/" + content_type)
        self.end_headers()
        self.wfile.write(body)

    def send_good_set_reply(self, content_type='xml'):
        if content_type == 'json':
            response = self.json_true_response
        else:
            response = self.xml_true_response

        self.send_response(200)
        self.send_header("Content-Length", len(response))
        self.send_header("Content-Type", "application/" + content_type)
        self.end_headers()
        self.wfile.write(response)
        self.wfile.flush()

    def send_bad_reply(self, message, content_type='xml'):

        if content_type == 'xml':
            reply = Element("Reply")
            result = SubElement(reply, "Result")
            result.text = "False"
            message = SubElement(reply, "Message")
            message.text = message
            reply = xml_tostring(reply, 'us-ascii')
        else:
            reply = json_dumps(
                {
                    "Result": "False",
                    "Message": message
                }
            )

        self.send_reply(reply, content_type)

    def getmainvalues(self, params, real_mode=False):
        """
        @param params: query string kv pairs
        @type params: dict
        @param real_mode: parse keywords the way the webserver does (True), or logically (False).
        @return:
        """
        if real_mode:
            if 'json' in params:
                json = True
            else:
                json = False

        else:
            json = params.pop('json', False)
            if params:
                raise Exception

        state = self.server.state.get_update(json)
        state = state.encode('ascii')
        if json:
            self.send_reply(state, 'json')
        else:
            self.send_reply(state, 'xml')

    def login(self, params, real_mode=False):
        try:
            val1 = params.pop("val1")  # user
            val2 = params.pop("val2")  # pwd
            loader = params.pop("loader")
            skipvalidate = params.pop("skipvalidate")
            if not real_mode and params:
                raise ArgumentError(' '.join(params), 1, 'xml')
        except KeyError as e:
            raise ArgumentError(e.args[0], 7115, 'xml', 'Username/password incorrect 7115')

        if self.server.state.login(val1, val2, loader, skipvalidate):
            self.send_good_set_reply()
        else:
            raise ArgumentError("Unknown", 2, 'xml')

    def logout(self, params, real_mode=False):

        if params and not real_mode:
            raise ArgumentError(' '.join(params), 1, 'xml')

        if self.server.state.logout():
            pass


class HelloServer(HTTPServer, metaclass=meta):
    """ A mock hello server that responds to calls.
    """
    def __init__(self, host='', port=12345, state=None):
        HTTPServer.__init__(self, (host, port), MyHTTPHandler)
        self.state = state or HelloState()


def test1():
    s = HelloServer()

    import threading
    import time
    import sys

    s.stdout = sys.stdout
    t = threading.Thread(None, s.serve_forever)
    t.daemon = True
    print("Serving forever")
    t.start()
    time.sleep(1)
    from http.client import HTTPConnection

    c = HTTPConnection("localhost", 12345)
    print("Requesting")
    c.request("GET", "?&call=getMainValues&json=True")
    print("Getting response")
    stuff = c.getresponse().read()
    out = "C:\\.replcache\\helloserver.html"
    with open(out, 'wb') as f:
        f.write(stuff)
    import webbrowser
    webbrowser.open_new_tab(out)

    from urllib.request import urlopen
    print(urlopen("http://192.168.1.4/webservice/interface/?&call=getMainValues&json=True").read())



def test2():
    s = HelloServer()
    s.handle_request()


def run_forever():
    s = HelloServer()
    s.serve_forever()

if __name__ == '__main__':
    try:
        test1()
    finally:
        sys.stdout.flush()
