"""

Created by: Nathan Starkweather
Created on: 11/03/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from http.server import HTTPServer, SimpleHTTPRequestHandler
from hello.mock.util import simple_xml_dump
from hello.mock.state import HelloState
from xml.etree.ElementTree import Element, SubElement, tostring as xml_tostring
from json import dumps as json_dumps
import traceback
import sys


def _stack_trace():
    rv = traceback.format_list(traceback.extract_stack())
    return rv

# custom error codes
E_UNKN_WTF = -1
E_UNEXPECTED_ARG = 1
E_MISSING_ARG = 2
E_BAD_LOGIN = 7115
E_UNRECOGNIZED_CMD = 7815
E_BAD_SYNTAX = 7816


class HelloServerException(Exception):
    def __init__(self, args):
        self.args = args,
        self.result = args
        self.message = args

    def json_reply(self, encoding='UTF-8'):
        """
        The json reply is simple enough to write out directly.
        Also, this avoids having to awkwardly make an OrderedDict
        with 'result' and 'message' passed in the proper order,
        followed by a call to json.dumps().
        """
        reply = """{
"result": "%s",
"message": "%s"
}""" % (self.result, self.message.replace("\"", "\\\""))
        return reply.encode(encoding)

    def xml_reply(self, encoding='UTF-8'):
        reply = Element("Reply")
        result = SubElement(reply, "Result")
        result.text = self.result
        message = SubElement(reply, "Message")
        message.text = self.message

        # for some reason, "True" replies encode in windows-1252,
        # but "False" replies (or at least some) encode in UTF-8 (???)
        return simple_xml_dump(reply, encoding)


class BadPath(HelloServerException):
    pass


class BadQueryString(HelloServerException):
    """ Couldn't parse query string, multiple arguments given,
    or other syntax & semantic errors.
    """
    def __init__(self, string):
        self.args = string,
        self.string = string
        self.result = string
        self.message = string


class UnrecognizedCommand(HelloServerException):
    """ User asked for something weird.
    """

    def __init__(self, cmd, json_rsp):
        self.args = cmd,
        self.cmd = cmd
        self.err_code = E_UNRECOGNIZED_CMD
        self.result = "False"
        self.message = "Unrecognized Command: %s" % self.err_code
        self.rsp_fmt = 'json' if json_rsp else 'xml'

        if json_rsp:
            self.reply = self.json_reply()
        else:
            self.reply = self.xml_reply()


class ArgumentError(UnrecognizedCommand):
    """ User asked for something known, but with bad arguments.
    """
    def __init__(self, what, err_code, json_rsp, msg=None):
        self.result = "False"
        self.what = what
        if msg:
            self.message = msg
        else:
            self.message = "Unrecognized %s: %s" % (what, err_code)
        self.args = self.message,
        self.err_code = err_code
        self.rsp_fmt = 'json' if json_rsp else 'xml'

        if json_rsp:
            self.reply = self.json_reply()
        else:
            self.reply = self.xml_reply()


class LoginError(ArgumentError):
    def __init__(self, json_rsp):
        self.result = "False"
        self.what = "Bad Login"
        self.message = 'Username/password incorrect %s' % E_BAD_LOGIN
        self.args = self.message,
        self.err_code = E_BAD_LOGIN
        self.rsp_fmt = 'json' if json_rsp else 'xml'

        if json_rsp:
            self.reply = self.json_reply()
        else:
            self.reply = self.xml_reply()


class MissingArgument(ArgumentError):
    def __init__(self, what, json_rsp):
        self.result = "False"
        self.what = what
        self.err_code = E_MISSING_ARG
        self.message = "Missing Argument: \"%s\". Code: %s" % (what, self.err_code)
        self.args = self.message,
        self.rsp_fmt = 'json' if json_rsp else 'xml'

        if json_rsp:
            self.reply = self.json_reply()
        else:
            self.reply = self.xml_reply()


class UnexpectedArgument(ArgumentError):
    def __init__(self, what, json_rsp):
        if not isinstance(what, str):
            if isinstance(what, dict):
                what = '(' + ', '.join("%s=%s" % i for i in what.items()) + ")"
            else:
                what = "(" + ", ".join(what) + ")"
        self.result = "False"
        self.what = what
        self.err_code = E_UNEXPECTED_ARG
        self.message = "Unexpected Argument(s) %s: %s" % (what, self.err_code)
        self.args = self.message,
        self.rsp_fmt = 'json' if json_rsp else 'xml'

        if json_rsp:
            self.reply = self.json_reply()
        else:
            self.reply = self.xml_reply()


class UnknownInternalError(HelloServerException):
    def __init__(self, msg=None):
        self.result = "False"
        self.what = "Unknown Error"
        self.message = _stack_trace()
        if msg:
            self.message = "\n".join((msg, self.message))
        self.args = self.message,
        self.err_code = E_UNKN_WTF
        self.rsp_fmt = 'json'
        self.reply = self.json_reply()


# from pysrc.snippets.metas import pfc_meta
# class HelloHTTPHandler(SimpleHTTPRequestHandler, metaclass=pfc_meta):
class HelloHTTPHandler(SimpleHTTPRequestHandler):
    """ This is the class that implements the actual command
     handling functionality. What we think of as the "Web Server"
     in our Hello software is split into two in python. In Python,
     an HTTPServer subclass is used essentially unmodified to
     handle the details of hosting the web service itself, while
     this class (SimpleHTTPRequestHandler subclass) performs
     all request handling.
    """

    json_true_response = """{
"result": "True",
"message": "True"
}""".encode('windows-1252')

    xml_true_response = '<?xml version="1.0" encoding="windows-1252" standalone="no" ?>' \
                        '<Reply>' \
                            '<Result>True</Result>' \
                            '<Message>True</Message>' \
                        '</Reply>'.encode('windows-1252')

    # real_mode: parse and handle arguments the same way
    # the real (labview) webserver handles them. Turning
    # this off parses arguments in a way that isn't stupid.

    real_mode = True

    # allow_json: allow json responses for server calls
    # in which the real hello server does not support
    # properly formatted json as responses. The existing
    # json responses are (according to Christian) hacks
    # used to produce json before a built-in json-dump method
    # was built into labview.

    allow_json = False

    def parse_path(self, path):
        """

        Parse the path. Currently, the webserver only supports
        /webservice/interface

        @param path: path to parse
        @return: query string
        """
        try:
            _, webservice, interface, qs = path.split("/", 3)
        except ValueError:
            raise BadPath(path)
        if webservice != "webservice" or interface != "interface":
            raise BadPath(path)
        return qs

    def do_GET(self):

        """
        Handle all GET responses. Identify a handler for the server
        request by parsing the query string for the "call" parameter,
        and searching for a method of the same name.

        If everything goes well, handler sends a reply and the function exists.
        If an error is raised, this function catches the exception and sends
        an appropriate reply.
        """

        try:
            qs = self.parse_path(self.path)
            call, params = self.parse_qs(qs, not self.real_mode)

            # A suffix is appended to the name of methods is important
            # to ensure that a malicious 3rd party can't access arbitrary
            # functions on the handler class by passing in names of known
            # private handler methods.
            # A proper fix would be using an explicit mapping to handle
            # dispatches. That can be on the todo list if/when hellohttphandler
            # and helloserver are merged into a single webserver class

            method_name = call + "_wsh"

            handler = getattr(self, method_name, None)
            if handler is None:
                raise UnrecognizedCommand(call, 'xml')
            handler(params, self.real_mode)
        except BadQueryString as e:
            self.send_error(400, "Bad query string: \"%s\"" % e.string)
        except ArgumentError as e:
            self.send_reply(e.reply, e.rsp_fmt)
        except UnrecognizedCommand as e:
            self.send_reply(e.reply, e.rsp_fmt)
        except BadPath as e:
            self.send_error(400, "Bad path, (%s) use webservice/interface" % e.args[0])
        except Exception:
            self.send_error(400, "Bad Path " + self.path)
            tb = traceback.format_exc()
            print("===========================================", file=sys.stderr)
            print("HelloHTTPHandler: Unknown Exception Caught", file=sys.stderr)
            print("===========================================", file=sys.stderr)
            print(tb, file=sys.stderr)
        finally:
            self.wfile.flush()

    def parse_qs(self, qs, strict=False):
        """
        @rtype: (str, dict)
        """
        qs = qs.lstrip("/?&")
        kvs = qs.split("&")

        assert kvs[0] not in {"/", "/?"}
        # if kvs[0] in {"/", "/?"}:
        #     kvs = kvs[1:]

        kws = {}
        for kv in kvs:
            k, v = kv.lower().split("=")
            if k in kws:
                if strict:
                    raise BadQueryString("Got multiple arguments for %s" % k)
            kws[k] = v

        call = kws.pop('call', None)
        if call is None:
            raise MissingArgument("Call", "xml")

        return call, kws

    def send_reply(self, body, content_type='xml'):
        self.send_response(200)
        self.send_header("Content-Length", len(body))
        self.send_header("Content-Type", "application/" + content_type)
        self.end_headers()
        if isinstance(body, str):
            body = body.encode("ascii")
        self.wfile.write(body)

    def send_reply_with_code(self, code, body, content_type='xml'):
        self.send_response(code)
        self.send_header("Content-Length", len(body))
        self.send_header("Content-Type", "application/" + content_type)
        self.end_headers()
        if isinstance(body, str):
            body = body.encode("ascii")
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

            reply = '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>' \
                                '<Reply>' \
                                '<Result>True</Result>' \
                                '<Message>%s</Message>' \
                                '</Reply>' % message
            reply = reply.encode('UTF-8')
        else:
            reply = json_dumps(
                {
                    "Result": "False",
                    "Message": message
                }
            )

        self.send_reply(reply, content_type)

    def getmainvalues_wsh(self, params, real_mode=False):
        """
        @param params: query string kv pairs
        @type params: dict
        @param real_mode: parse keywords the way the webserver does (True), or logically (False).
        @return:
        """

        json = self._get_json_from_kw(params, real_mode)
        if params:
            raise UnexpectedArgument(params, json)

        state = self.server.state.get_update(json)
        if state:
            self.send_reply(state, 'json' if json else 'xml')
        else:
            raise UnknownInternalError("Failed to get update from server")

    def _get_json_from_kw(self, params, real_mode):

        json = params.pop('json', None)

        # json not in kw
        if json is None:
            return False

        # if json is passed to the real hello webserver,
        # the response is json regardless of the actual value
        if real_mode:
            return True

        jl = json.lower()

        valid_false = {'0', 'false', ""}
        valid_true = {'1', 'true'}

        if jl in valid_false:
            return False
        elif jl in valid_true:
            return True
        else:
            raise UnexpectedArgument("json=%s" % json, 'xml')

    def login_wsh(self, params, real_mode=False):

        if self.allow_json:
            json = self._get_json_from_kw(params, real_mode)
        else:
            json = False

        try:
            val1 = params.pop("val1")  # user
            val2 = params.pop("val2")  # pwd
        except KeyError as e:
            if not self.real_mode:
                raise MissingArgument(e.args[0], json)
            else:
                raise LoginError(json)

        # No one knows what these two keys do.
        # They don't seem to be necessary to login
        # (at least when I tested 12/5/14...)
        loader = params.pop("loader", "")
        skipvalidate = params.pop("skipvalidate", "")

        if not real_mode and params:
            raise UnexpectedArgument(params, json)

        if self.server.state.login(val1, val2, loader, skipvalidate):
            return self.send_good_set_reply('json' if json else 'xml')
        else:

            raise LoginError(json)

    def logout_wsh(self, params, real_mode=False):

        if self.allow_json:
            json = self._get_json_from_kw(params, real_mode)
        else:
            json = False

        if params and not real_mode:
            raise UnexpectedArgument(params, json)

        if self.server.state.logout():
            return self.send_good_set_reply('json' if json else 'xml')
        else:
            raise UnknownInternalError("Failed to logout")

    def getversion_wsh(self, params, real_mode=False):

        if self.allow_json:
            json = self._get_json_from_kw(params, real_mode)
        else:
            json = False

        if not real_mode:
            if params:
                raise UnexpectedArgument(params, json)

        version = self.server.state.getversion(json)
        if version:
            self.send_reply(version, json)
        else:
            raise UnknownInternalError("Error Getting Version Info")

    def getmaininfo_wsh(self, params, real_mode=False):
        if self.allow_json:
            json = self._get_json_from_kw(params, real_mode)
        else:
            json = False

        if not real_mode and params:
            raise UnexpectedArgument(params, json)

        main_info = self.server.state.getmaininfo(json)
        if main_info:
            self.send_reply(main_info, json)
        else:
            raise UnknownInternalError("Error Getting Main Info")


class HelloServer(HTTPServer):
    """ A mock hello server that responds to calls.
    """
    def __init__(self, host='', port=12345, state=None):
        HTTPServer.__init__(self, (host, port), HelloHTTPHandler)
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
    c.request("GET", "/webservice/interface/?&call=getMainValues")
    print("Getting response")
    stuff = c.getresponse().read()
    out = "C:\\.replcache\\helloserver.xml"
    with open(out, 'wb') as f:
        f.write(stuff)
    import webbrowser
    webbrowser.open_new_tab(out)

    from urllib.request import urlopen
    print(urlopen("http://localhost:12345/webservice/interface/?&call=getMainValues").read().decode())


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
