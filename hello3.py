"""

Created by: Nathan Starkweather
Created on: 09/11/2014
Created in: PyCharm Community Edition

General purpose module for making REPL friendly
hello functions and such. Compile some common functions
from other modules/ipython sessions/etc.

Maybe turn into __init__.py?
"""
from collections import OrderedDict
from http.client import HTTPConnection, HTTPException, HTTPSConnection
import ssl
import datetime
import io

__author__ = 'Nathan Starkweather'

from xml.etree.ElementTree import XMLParser, XML as parse_xml
from json import loads as json_loads
import re
from time import time
import types
import logging
import ipaddress
import traceback
import socket
import itertools

from hello import _hello


class BadError(Exception):
    """ Encompasses all things bad. """
    pass


class HelloError(BadError):
    """ Problem with Hello app class. """
    pass


class ServerCallError(HelloError):
    pass


class TrueError(ServerCallError):
    """ Server was stupid. """

class NotLoggedInError(ServerCallError):
    pass



AuthError = ServerCallError


class XMLError(HelloError):
    """ Problem with XML returned from a server call """
    pass


_sanitize = re.compile(r"([\s:%/])").sub

# todo: add all url substitution thingies.
_sanitize_map = {
    ':': '',
    ' ': '_',
    '/': '%2F',
    '%': '%25'
}


def _sanitize_cb(m):
    return _sanitize_map[m.group(0)]


def sanitize_url(url):
    return _sanitize(_sanitize_cb, url)


def parse_rsp(rsp):
    parser = XMLParser()

    # The default XMLParser, when it comes from an accelerator,
    # can define an internal _parse_whole API for efficiency.
    # It can be used to parse the whole source without feeding
    # it with chunks.
    parse_whole = getattr(parser, "_parse_whole")
    if parse_whole:
        return parse_whole(rsp)

    while True:
        data = rsp.read(65536)
        if not data:
            break
        parser.feed(data)
    return parser.close()


def open_hello(app_or_ipv4):
    if isinstance(app_or_ipv4, _hello._BaseHelloApp):
        return app_or_ipv4
    else:
        return HelloApp(app_or_ipv4)


class DoRequestMixin():
    def do_request(self, meth, url, body=None, headers=None):
        headers = headers or {}
        self.request(meth, url, body, headers)
        return self.getresponse()


class LVWSHTTPConnection(DoRequestMixin, HTTPConnection):
    pass

class LVWSHTTPSConnection(DoRequestMixin, HTTPSConnection):
    def __init__(self, *args, **kw):
        context = ssl._create_unverified_context()
        super().__init__(*args, context=context, **kw)
        self.cert_reqs = 'CERT_NONE'
        self.ca_certs = None
        self.ca_cert_dir = None


import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class HTTPSSession():
    def __init__(self, host, port=None, timeout=5):
        super().__init__()
        self._base = "https://%s" % host
        if port:
            self._base += ":%d" % port
        self.sess = requests.Session()
        self.timeout = timeout

        # For public access (api compatibility)
        self.host = host
        self.port = port
    def do_request(self, meth, url, body=None, headers=None):
        url = self._base + url
        rsp = self.sess.request(meth, url, body, None, timeout=self.timeout, verify=False)
        # XXX Sloppy. Refactor HelloApp to not use read()
        file = io.BytesIO(rsp.content)
        rsp.read = file.read
        return rsp
    def connect(self):
        self.sess = requests.Session()
    def close(self):
        self.sess = requests.Session()


# modes
AUTO = 0
MAN = 1
OFF = 2


class BaseHelloApp(_hello._BaseHelloApp):
    headers = {}
    ConnectionFactory = HTTPSSession

    def __init__(self, ipv4, headers=None, retry_count=3, timeout=5, verbose_errors=False, logger=None):
        """
        @param ipv4: ipv4 address to connect to (string eg 192.168.1.1:80)
        @param headers: headers to pass on each http connection
        @param retry_count: how many times to retry a connection on failure
                            set to 0 to try forever.
        """
        super().__init__()
        self.headers = self.headers.copy()
        self.headers.update(headers or {})
        self._urlbase = "/webservice/interface/"
        self.retry_count = retry_count
        self.verbose_errors = verbose_errors

        self._ipv4 = ipv4
        
        self._connection = self._init_connection(ipv4, None, timeout)
        self._connection.connect()

        self._parse_rsp = parse_rsp
        self._logger = logger or logging.Logger("%s: %s" % (self.__class__.__name__, ipv4))

    def _init_connection(self, host, port=None, timeout=5):
        return self.ConnectionFactory(host, port, timeout=timeout)

    def close(self):
        if self._connection:
            self._connection.close()

    def reconnect(self):
        self._connection.close()
        self._connection.connect()

    def settimeout(self, timeout):
        if not isinstance(timeout, int) or timeout < 0:
            raise ValueError(timeout)
        self._connection.timeout = timeout

    @property
    def ipv4(self):
        return self._ipv4

    def _do_request(self, url):
        if self.retry_count > -1:
            it = range(self.retry_count + 1)
        else:
            it = itertools.count(0)  # forever
        for _ in it:
            try:
                return self._connection.do_request('GET', url, None, self.headers)
            except (ConnectionError, HTTPException, TimeoutError) as e:
                err = e
                self.reconnect()
            except Exception as e:
                err = e
                if self.verbose_errors:
                    msg = "%s(%s)" % (err.__class__.__name__, ", ".join(str(a) for a in err.args))
                    self._logger.warning("=====================================")
                    self._logger.warning("ERROR OCCURRED DURING REQUEST")
                    self._logger.warning("IP ADDRESS: %s", self._ipv4)
                    self._logger.warning("REQUESTED URL: <%s>", url)
                    self._logger.warning("MESSAGE: %s", msg)
                    self._logger.warning("=====================================")
                self.reconnect()
        raise err

    def _send_request_raw(self, url):
        """
        @return: http response object
        @rtype: http.client.HTTPResponse
        """
        rsp = self._do_request(url)
        cookie = rsp.headers.get("Set-Cookie")
        if cookie:
            c = cookie.split(';', 1)[0]  # works on empty strings too
            if c:
                self.headers['Cookie'] = c
            else:
                del self.headers['Cookie']
        return rsp

    def call(self, call, **kw):
        # ensure call is the first parameter argument
        # The webserver doesn't require this, but it 
        # Historically made life easier when debugging
        # so continue to follow convention here. 
        args = "&".join("%s=%s"%(k,v) for k, v in kw.items())
        query = "?call=%s%s%s" % (call, "&" if args else "", args)
        return self.send_request(query)

    def call_validate(self, call, **kw):
        json = kw.get('json', False)
        rsp = self.call(call, **kw)
        return self._validate_rsp(rsp, json)

    def send_request(self, query):
        """
        @type query: str
        @rtype: http.client.HTTPResponse

        Call hello using the provided query string.
        Query string must be built explicitly.
        """
        url = self._urlbase + query
        return self._send_request_raw(url)

    def _validate_rsp(self, rsp, json):
        if json:
            data = json_loads(rsp.read().decode())
            return self._verify_json(data)
        else:
            data = HelloXML(rsp)
            return self._verify_xml(data)

    def _verify_xml(self, xml):
        if not xml.result:
            raise self._verify_fail(xml.data)
        return xml

    def _verify_json(self, json):
        """ The json reply content is non-normalized
        for different API calls and responses. In 
        particular, fail response may be "result" "message"
        structure with "result" == False and "message"
        an error message, while the success response 
        may just be the body of the json itself. 

        This is stupid as shit but I have to deal with it. 
        """
        noresult = object()
        result = json.get('Result', noresult)
        assert 'result' not in json and 'message' not in json, json
        if result is noresult:
            return json
        if not result:
            raise self._verify_fail(json['Message'])
        return json
    
    def _verify_fail(self, message):
        """ Return exception class to be raised by caller.
        (Save the frames!)
        """
        if isinstance(message, str):
            if message.startswith("No user associated"):
                return NotLoggedInError(message)
            return ServerCallError(message)
        else:
            return ServerCallError(message)


def _retry_on_auth_fail(func):
    def wrapper(self, *args, **kw):
        err = None
        try:
            rv = func(self, *args, **kw)
        except NotLoggedInError as e:
            err = e
        else:
            return rv
        if self._user and self._password:
            self.login(self._user, self._password)
            return func(self, *args, **kw)
        else:
            raise err
    return wrapper


class HelloAPI(BaseHelloApp):
    def login(self, user, pwd):
        return self.call_validate('login', val1=user, val2=pwd, json=True)

    def logout(self):
        return self.call_validate('logout', json=True)

    def startbatch(self, name):
        return self.call_validate('setStartBatch', val1=name)

    def endbatch(self):
        return self.call_validate('setendbatch')

    def getAlarms(self, mode, nalarms, id):
        return self.call_validate('getAlarms', mode=mode, val1=nalarms, val2=id)

    def getAlarmList(self):
        return self.call_validate('getAlarmList')

    def getUnAckCount(self):
        return self.call_validate('getUnAckCount')

    def getReport(self, mode, type, val1, val2, timeout):
        # Thanks, Chen!
        url = "/webservice/getReport/?&mode=%s&type=%s&val1=%s&val2=%s&timeout=%s" % \
                (mode, type, val1, val2, timeout)
        rsp = self._send_request_raw(url)
        return self._validate_rsp(rsp, False)

    def getBatches(self):
        return self.call_validate('getBatches')

    def getfile(self, filename):
        # Thanks, Chen! (I didn't do this)
        url = "/webservice/getfile/?&getfile=" + filename
        rsp = self._send_request_raw(url)
        return rsp.read()

    def set(self, group, mode, val1, val2):
        if val2 is None:
            return self.call_validate('set', group=group, mode=mode, val1=val1)
        else:
            return self.call_validate('set', group=group, mode=mode, val1=val1, val2=val2)

    def getDORAValues(self):
        return self.call_validate('getDORAValues')

    def getMainValues(self):
        return self.call_validate('getMainValues', json=True)

    def setconfig(self, group, name, val):
        return self.call_validate('setconfig', group=group, name=name, val=val)

    def setpumpa(self, mode, val):
        return self.call_validate('setpumpa', val1=mode, val2=val)

    def setpumpb(self, mode, val):
        return self.call_validate('setpumpb', val1=mode, val2=val)

    def setpumpc(self, mode, val):
        return self.call_validate('setpumpc', val1=mode, val2=val)

    def setpumpsample(self, mode, val):
        return self.call_validate('setpumpsample', val1=mode, val2=val)


def lowercase_methods(cls):
    from types import FunctionType
    lower = {}
    for k,v in cls.__dict__.items():
        if isinstance(v, FunctionType) and k[0] != "_":
            lower[k.lower()] = v
    for k, v in lower.items():
        setattr(cls, k, v)
    return cls


@lowercase_methods
class HelloApp(BaseHelloApp):

    def __init__(self, ipv4, headers=None, retry_count=3, timeout=socket.getdefaulttimeout(), verbose_errors=False):
        super().__init__(ipv4, headers, retry_count, timeout, verbose_errors)
        self._user = ""
        self._password = ""

    def login(self, user='user1', pwd='12345'):
        query = "?&call=login&val1=%s&val2=%s&json=1" % (user, pwd)
        rsp = self.send_request(query)
        return self._validate_rsp(rsp, True)

    def logout(self):
        query = "?&call=logout"
        rsp = self.send_request(query)
        return self._validate_rsp(rsp, False)

    def startbatch(self, name):
        name = name.replace(" ", "+")
        query = "?&call=setStartBatch&val1=%s" % name
        rsp = self.send_request(query)
        return self._validate_rsp(rsp, False)

    def endbatch(self):
        query = "?&call=setendbatch"
        rsp = self.send_request(query)
        xml = HelloXML(rsp.read())
        if not xml.result:
            if "no batch currently running" in xml.data.lower():
                return True
            else:
                return self._verify_xml(xml)
        return True

    def getAlarms(self, mode='first', val1='100', val2='1'):
        query = "?&call=getAlarms&mode=%s&val1=%s&val2=%s" % (mode, val1, val2)
        rsp = self.send_request(query)
        xml = HelloXML(rsp)
        if not xml.result:
            raise ServerCallError(xml.msg)
        return xml.data['Alarms']

    def getAlarmList(self):
        query = "?&call=getAlarmList"
        rsp = self.send_request(query)
        xml = HelloXML(rsp)
        if not xml.result:
            raise ServerCallError(xml.msg)
        return xml.data['cluster']

    def getUnAckCount(self):
        query = "?&call=getUnAckCount"
        rsp = self.send_request(query)
        xml = HelloXML(rsp)
        if not xml.result:
            raise ServerCallError(xml.msg)
        return int(xml.data)

    def getReport(self, mode, type, val1, val2='', timeout=120000):
        """
        @param mode: 'byBatch' or 'byDate'
        @param type: data, recipe steps, errors, or user events
        @param val1: ID of batch, or start date
        @param val2: blank if byBatch, or end date
        @param timeout: who knows.
        """
        # url got weird because Chen because LabVIEW
        url = "/webservice/getReport/?&mode=%s&type=%s&val1=%s&val2=%s&timeout=%s" % \
                (mode, type, val1, val2, timeout)
        rsp = self._send_request_raw(url)

        # getreport uses a different webserver
        # and chen used a different json message structure
        # ??? so we have to check for errors manually
        data = json_loads(rsp.read().decode())
        message = data['message']
        if not message:
            err = data['error']
            if err.startswith("No user associated"):
                raise NotLoggedInError(err)
            raise ServerCallError(err)
        return message

    def getBatches(self):
        query = "?&call=getBatches&loader=Loading+batches..."
        rsp = self.send_request(query)
        xml = BatchListXML(rsp)
        return self._verify_xml(xml)

    def getreport_byname(self, type, name):
        return self.getReport('byBatch', type, name)

    def getdatareport_bybatchid(self, val1):
        """
        @return: report as a byte string
        @rtype: bytes
        """
        fname = self.getReport('byBatch', 'process_data', val1)
        return self.getfile(fname)

    def getreport_bydate(self, type, d1, d2):
        s1 = int(d1.timestamp())
        s2 = int(d2.timestamp())
        fname = self.getReport('byDate', type, s1, s2)
        return self.getfile(fname)

    def getfile(self, fname):
        # chen fucked up the url on the new protocol so bad I had to
        # restructure helloapp to sensibly work with it
        # and then fucked it up again in 3.0
        # /getfile/?&getfile? really? really?
        url = "/webservice/getfile/?&getfile=" + fname
        rsp = self._send_request_raw(url)
        return rsp.read()

    def getdatareport_bybatchname(self, name):
        xml = self.getBatches()
        try:
            id = xml.getbatchid(name)
        except KeyError:
            raise HelloError("Bad batch name given- batch not found: " + name) from None
        return self.getdatareport_bybatchid(id)

    def setdo(self, mode, n2, o2=None):
        # Val1 = N2 sp (or auto sp)
        # Val2 = O2 sp (unused if auto mode)

        if o2 is None:
            query = "?&call=set&group=do&mode=%s&val1=%s" % (mode, n2)
        else:
            query = "?&call=set&group=do&mode=%s&val1=%s&val2=%s" % (mode, n2, o2)
        rsp = self.send_request(query)
        return self._validate_rsp(rsp, False)

    def setph(self, mode, co2, base=None):
        # Val1 = CO2 sp (or auto sp)
        # Val2 = base sp (unused if auto mode)
        if base is None:
            query = "?&call=set&group=ph&mode=%s&val1=%s" % (mode, co2)
        else:
            query = "?&call=set&group=ph&mode=%s&val1=%s&val2=%s" % (mode, co2, base)
        rsp = self.send_request(query)
        return self._validate_rsp(rsp, False)

    def setmg(self, mode, val):
        query = "?&call=set&group=maingas&mode=%s&val1=%s" % (mode, val)
        rsp = self.send_request(query)
        return self._validate_rsp(rsp, False)

    def setag(self, mode, val):
        query = "?&call=set&group=agitation&mode=%s&val1=%s" % (mode, val)
        rsp = self.send_request(query)
        return self._validate_rsp(rsp, False)

    def settemp(self, mode, val):
        query = "?&call=set&group=temperature&mode=%s&val1=%s" % (mode, val)
        rsp = self.send_request(query)
        return self._validate_rsp(rsp, False)

    def set_mode(self, group, mode, val, val2=None):
        query = "?&call=set&group=%s&mode=%s&val1=%s" % (group, mode, val)
        if val2 is not None:
            query += "&val2=%s"%val2
        rsp = self.send_request(query)
        return self._validate_rsp(rsp, False)

    def getDORAValues(self):
        query = "?&call=getDORAValues"
        rsp = self.send_request(query)
        xml = HelloXML(rsp)

        if not xml.result:
            raise ServerCallError(xml.msg)

        # getDORAValues ends up returning a blank element
        # for the name of the cluster, so the dict ends up
        # being {None: DoraValues}
        return xml.data[None]

    def batchrunning(self):
        return self.getDORAValues()['Batch'] != '--'

    def reciperunning(self):
        return self.getDORAValues()['Sequence'] != 'Idle'

    def reactorname(self):
        return self.getDORAValues()['Machine Name']

    def getMainValues(self):
        query = "?&call=getMainValues&json=true"
        rsp = self.send_request(query)
        mv = json_loads(rsp.read().decode('utf-8'))
        return mv

    def loadbag(self, expirationDate='', part='', serial='', pham='', phab='', phat='', 
                phbm='', phbb='', phbt='', doam='', doab='', dobm='', dobb=''):
        raise NotImplementedError

    # backward compatibility
    gmv = getMainValues
    gpmv = getMainValues

    def setconfig(self, group, name, val):
        name = sanitize_url(name)
        query = "?&call=setconfig&group=%s&name=%s&val=%s" % (group, name, str(val))
        rsp = self.send_request(query)
        return self._validate_rsp(rsp, False)

    def setpumpa(self, mode=0, val=0):
        query = "?&call=setpumpa&val1=%d&val2=%d" % (mode, val)
        return self._validate_rsp(self.send_request(query), False)

    def setpumpb(self, mode=0, val=0):
        query = "?&call=setpumpb&val1=%d&val2=%d" % (mode, val)
        return self._validate_rsp(self.send_request(query), False)

    def setpumpc(self, mode=0, val=0):
        query = "?&call=setpumpc&val1=%d&val2=%d" % (mode, val)
        return self._validate_rsp(self.send_request(query), False)

    def setpumpsample(self, mode=0, val=0):
        query = "?&call=setpumpsample&val1=%d&val2=%d" % (mode, val)
        return self._validate_rsp(self.send_request(query), False)

    def trycal(self, sensor, val1, target1, val2=None, target2=None):
        """
        @param sensor: sensor: "doa", "dob", "pha", "phb", "level", "pressure"
        @param val1: value returned by getRawValue()
        @param target1: pv that val1 actually corresponds to (value entered by user)
        @param val2: value returend by getRawValue()
        @param target2: pv that val1 actually corresponds to (value entered by user)
        """
        if val2 or target2:
            # two point cal
            query = "?&call=trycal&sensor=%s&val1=%s&target1=%s&val2=%s&target2=%s" % (sensor, val1, target1,
                                                                                       val2, target2)
        else:
            # one point cal
            query = "?&call=trycal&sensor=%s&val1=%s&target1=%s" % (sensor, val1, target1)

        rsp = self.send_request(query)
        return self._validate_rsp(rsp, False)

    def getRawValue(self, sensor):
        query = "?&call=getRawValue&sensor=" + sensor
        rsp = self.send_request(query)
        xml = HelloXML(rsp)
        if not xml.result:
            raise ServerCallError(xml.data)
        return float(xml.data)

    def getVersion(self):
        query = "?&call=getVersion"
        rsp = self.send_request(query)
        xml = HelloXML(rsp)
        if not xml.result:
            raise ServerCallError(xml.data)
        return xml.data['Versions']

    # Convenience functions
    def getmodelsize(self):
        return int(self.getVersion()['Model'][4:])

    def getdopv(self):
        return self.gpmv()['do']['pv']

    def getagpv(self):
        return self.gpmv()['agitation']['pv']

    def getautoagvals(self):
        mv = self.gpmv()
        ag = mv['agitation']
        return ag['pv'], ag['sp']

    def getmanagvals(self):
        mv = self.gpmv()
        ag = mv['agitation']
        return ag['pv'], ag['man']

    def gettemppv(self):
        return self.gpmv()['temperature']['pv']

    def getautotempvals(self):
        temp = self.gpmv()['temperature']
        return temp['pv'], temp['sp']

    def getmantempvals(self):
        temp = self.gpmv()['temperature']
        return temp['pv']['man']

    def getConfig(self):
        query = "?&call=getConfig"
        rsp = self.send_request(query)
        xml = HelloXML(rsp)
        self._verify_xml(xml)
        # James renamed the clusters to SV_Air
        # and SV_Mag to make it easier for him
        # to keep track of. The "proper" solution
        # would be to just return the proper XML 
        # element when parsing. The easiest solution
        # is to just check for the key, since conversion
        # from XML to dict occurs upstream. 
        try:
            return xml.data['System_Variables_Mag']
        except KeyError:
            return xml.data['System_Variables_Air']

    def getRecipes(self, loader="Loading+recipes"):
        query = "?&call=getRecipes&loader=" + loader
        rsp = self.send_request(query)
        xml = HelloXML(rsp)
        if not xml.result:
            raise ServerCallError(xml.msg)
        return xml.data.split(",")
        
    def getTrendData(self, span, group):
        query = "?&call=getTrendData&span=%s&group=%s&json=1" % (span, group)
        rsp = self.send_request(query)
        return self._validate_rsp(rsp, True)

    def __repr__(self):
        h = self._connection.host or ""
        p = self._connection.port or ""
        c = ":" if p else ""
        return "%s(\"%s%s%s\")" % (self.__class__.__name__, h, c, p)

    __str__ = __repr__


class HelloXML():

    def __init__(self, xml):
        if isinstance(xml, str):
            root = parse_xml(xml.encode())
        elif isinstance(xml, bytes):
            root = parse_xml(xml)
        else:
            root = parse_rsp(xml)

        self._parse_types = self._get_parse_types()
        self._init(root)

    def _get_parse_types(self):
        return {
            'DBL': self.parse_float,
            'I32': self.parse_int,
            'I16': self.parse_int,
            'U16': self.parse_int,
            'U8': self.parse_int,
            'Cluster': self.parse_cluster,
            'String': self.parse_string,
            'Boolean': self.parse_bool,
            'SGL': self.parse_float,
            'Array': self.parse_array
        }

    def _init(self, root):
        self._parsed = False

        # begin
        data = self.begin_parse(root)
        self.parse_dict = data['Reply']
        self.result = self.parse_dict['Result'] == 'True'
        self.data = self.msg = self.parse_dict['Message']

        # if self.msg == 'True':
        #     raise TrueError("Expected response, got \"True\"")

        self._parsed = True

    # probably unnecessary: access self.data directly
    def getdata(self):
        if self._parsed:
            return self.data
        else:
            raise BadError("No data!")

    def begin_parse(self, root):
        rv = {}
        self.parse(root, rv)
        return rv

    def parse(self, e, ns):
        name = e.tag
        children = list(e)
        if not children:
            ns[name] = e.text
        else:
            val = {}
            self.parse_children(children, val)
            ns[name] = val

    def parse_children(self, elems, ns):
        """
        @param elems: elements
        @type elems: list[xml.etree.ElementTree.Element]
        """
        get_parser = self._parse_types.get
        for c in elems:
            parser = get_parser(c.tag)
            if parser:
                parser(c, ns)
            else:
                self.parse(c, ns)

    def parse_int(self, e, ns):
        name = e[0].text
        val = e[1].text
        val = int(val or 0)
        ns[name] = val

    def parse_bool(self, e, ns):
        name = e[0].text
        val = e[1].text
        val = bool(val or False)
        ns[name] = val

    def parse_string(self, e, ns):
        name = e[0].text
        val = e[1].text
        val = str(val)
        ns[name] = val

    def parse_float(self, e, ns):
        name = e[0].text
        val = e[1].text
        val = float(val or 0.0)
        ns[name] = val

    def parse_cluster(self, e, ns):
        val = {}
        name = e[0].text
        self.parse_children(e[2:], val)
        ns[name] = val
    parse_array = parse_cluster


def _parse_date(s):
    return datetime.datetime.strptime(s, "%I:%M:%S %p\n %m/%d/%Y") 

class BatchEntry():
    """ The list of batch entries returned by the
    getBatches call is very unfortunate to work with.

    I tried to avoid having to use a whole object
    to represent each batch, but I think it will be
    easier to create a batch object and then manipulate
    lists of batch objects, rather than trying to slopily
    move them around in any other form.
    """

    def __init__(self, id, name='', serial_number=0, user='', start_time=0, stop_time=0,
                 product_number=0, rev=0):
        self.id = id
        self.name = name
        self.serial_number = serial_number
        self.user = user

        self.start_time = _parse_date(start_time)
        if stop_time == 'None':
            stop_time = None
        stop_time = _parse_date(stop_time) if stop_time else datetime.datetime.now()
        self.stop_time = stop_time

        assert self.stop_time >= self.start_time, (self.start_time, self.stop_time)  # server's fault not mine
        # if self.stop_time < self.start_time:
            # self.stop_time = self.start_time + datetime.timedelta(days=1)

        self.product_number = product_number
        self.rev = rev

    def __getitem__(self, item):
        """
        Let class pretend to be a dict for some internal use.
        """
        key = item.lower().replace(' ', '_')
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def copy(self):
        cls = self.__class__
        return cls(self.id, self.name, self.serial_number, self.user, self.start_time,
                   self.stop_time, self.product_number, self.rev)

    def __repr__(self):
        return "%s: id: %s name: %s user: %s start time: %s stop time: %s" % \
                                    (self.__class__.__name__, self.id, self.name,
                                     self.user, self.start_time, self.stop_time)


class BatchListXML(HelloXML):
    """ The xml from getBatches is stupid and needs
    a different parsing scheme, and its own class.
    """

    def _init(self, root):

        self._parsed = False

        # getbatches can send a zero sized array
        # with a single empty batch element (???)
        # so we have to specially handle it, because
        # fuck labview.
        dsize = root.find("./Message/Array/Dimsize")
        if dsize is not None and dsize.text == '0':
            self.names_to_batches = {}
            self.ids_to_batches = {}
            self.max_id = None
            self.parse_dict = {}
            self.result = True
            self._parsed = True
            self.data = {}
        else:
            data = self.begin_parse(root)

            # Bad things happen if this code tries to proceed
            # with a TrueBug response, so raise an error here.
            if data['Reply']['Message'] == 'True':
                raise TrueError()

            self.parse_dict = data
            self.reply = data['Reply']
            self.result = self.reply['Result'] == 'True'

            if self.result:
                ids_to_batches = self.reply['Message']['Batches (cluster)']

                # map names <-> ids
                # note that many batches may have the same name.
                # Newer names override older names,
                # where 'newer' means 'higher id'
                names_to_batches = {}
                for entry in ids_to_batches.values():
                    name = entry["Name"]
                    id = int(entry['ID'])
                    if name in names_to_batches:
                        if id > int(names_to_batches[name]['ID']):
                            names_to_batches[name] = entry
                    else:
                        names_to_batches[name] = entry

                self.names_to_batches = names_to_batches
                self.ids_to_batches = self.data = OrderedDict(sorted(ids_to_batches.items()))
                self.max_id = max(self.ids_to_batches.keys())
                self._parsed = True
            else:
                self.names_to_batches = self.ids_to_batches = {}
                self.data = self.reply['Message']

    def getbatches(self):
        return list(self.ids_to_batches.values())

    def __getitem__(self, v):
        return self.get(v)

    def get(self, key):
        try:
            return self.names_to_batches[key]
        except KeyError:
            pass
        try:
            return self.ids_to_batches[key]
        except KeyError:
            pass
        raise KeyError(key)

    def getdata(self):
        if self._parsed:
            return self.ids_to_batches
        else:
            raise BadError("No data!")

    def getbatchname(self, id):
        return self.ids_to_batches[id].name

    def getbatchid(self, name):
        name = name.lower()
        return self.names_to_batches[name].id

    def parse_batch(self, e):
        val = {}
        self.parse_children(e[2:], val)
        g = val.get  # brevity
        b = BatchEntry(g('ID'), g('Name'), g('Serial Number'),
                       g('User'), g('Start Time'), g('Stop Time'),
                       g('Product Number'), g('Rev'))
        return b

    def parse_cluster(self, e, ns):
        cname = e[0].text
        if cname == 'Batch':
            val = self.parse_batch(e)
        else:
            val = {}
            self.parse_children(e[2:], val)
        name = val['ID']
        ns[name] = val


def __test2():
    b = HelloApp('192.168.1.6').getBatches()
    d = b.data

    def dump_dict(d, name=''):
        if name:
            print("Dumping %s" % name)
        for k, v in d.items():
            print(k, "=", v)
    dump_dict(d)
    dump_dict(b.names_to_batches, "Names to batches")
    dump_dict(b.ids_to_batches, "Ids to batches")


def __test3():
    print(HelloApp('192.168.1.6').getdatareport_bybatchid(2))


def __test4():
    print(HelloApp('192.168.1.6').getdatareport_bybatchname('KLA0-10-200'))


def __test5():
    HelloApp('192.168.1.6').getDORAValues()

if __name__ == '__main__':
    pass
    #__test2()
    #__test3()
    #__test4()
    #__test5()
