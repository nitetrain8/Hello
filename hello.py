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
from http.client import HTTPConnection, BadStatusLine

__author__ = 'Nathan Starkweather'

from xml.etree.ElementTree import XMLParser, XML as parse_xml
from json import loads as json_loads
from re import compile as re_compile
from time import time
import types
import logging


class BadError(Exception):
    """ Encompases all things bad. """
    pass


class HelloError(BadError):
    """ Problem with Hello app class. """
    pass


class ServerCallError(HelloError):
    pass


class TrueError(ServerCallError):
    """ Server was stupid and returned "True" on a Get call.
    """


class AuthError(ServerCallError):
    """ Authentication Error. Most likely due to
    failure to properly maintain state across multiple
    server calls.
    """
    pass


class XMLError(HelloError):
    """ Problem with XML returned from a server call """
    pass


_sanitize = re_compile(r"([\s:%/])").sub

# todo: add all url substitution thingies.
_sanitize_map = {
    ':': '',
    ' ': '_',
    '/': '%2F',
    '%': '%25'
}


def _sanitize_cb(m):
    """
    @type m: _sre.SRE_Match
    """
    return _sanitize_map[m.group(0)]


def sanitize_url(url, cb=_sanitize_cb):
    return _sanitize(cb, url)


# noinspection PyProtectedMember, PyUnusedLocal
def parse_rsp(rsp):
    parser = XMLParser()
    if hasattr(parser, '_parse_whole'):
        # The default XMLParser, when it comes from an accelerator,
        # can define an internal _parse_whole API for efficiency.
        # It can be used to parse the whole source without feeding
        # it with chunks.
        return parser._parse_whole(rsp)

    while True:
        data = rsp.read(65536)
        if not data:
            break
        parser.feed(data)
    return parser.close()


class LVWSHTTPConnection(HTTPConnection):
    def do_request(self, meth, url, body=None, headers=None):
        headers = headers or {}
        self.request(meth, url, body, headers)
        return self.getresponse()


class BaseHelloApp():
    _headers = {}
    _url_template = "http://%s/webservice/interface/"

    def __init__(self, ipv4, headers=None, retry_count=3):
        """
        @param ipv4: ipv4 address to connect to (string eg 192.168.1.1:80)
        @param headers: headers to pass on each http connection
        @param retry_count: how many times to retry a connection on failure
                            set to 0 to try forever.
        """
        self._urlbase = "/webservice/interface/"
        self.retry_count = retry_count

        self._ipv4 = ipv4
        self._host, self._port = self._parse_ipv4(ipv4)
        self._connection = self._init_connection(self._host, self._port)

        # create instance copy
        self.headers = self._headers.copy()
        if headers is not None:
            self.headers.update(headers)

        self._parse_rsp = parse_rsp

        # setup logger and export some methods
        self._logger = logging.Logger(self._calc_logger_name(ipv4))
        self._log = self._logger.log
        self._debug = self._logger.debug
        self._warn = self._logger.warning
        self._info = self._logger.info

    def _calc_logger_name(self, ipv4):
        return "%s: %s" % (self.__class__.__name__, ipv4)

    def _parse_ipv4(self, ipv4):
        """
        @param ipv4: ipv4 internet address
        @type ipv4: str
        @return: (host, port) tuple
        @rtype: (str, int)

        Parse IPV4 address into host and port. Default to
        port 80 (HTTP port) if none given.
        """
        if ':' in ipv4:
            host, port = ipv4.split(':')
        else:
            host = ipv4
            port = 80
        return host, port

    def _init_connection_fromipv4(self, ipv4):
        """
        @param ipv4: IPV4 internet address
        @type ipv4: str
        @return: HTTPConnection object
        @rtype: HTTPConnection
        """
        host, port = self._parse_ipv4(ipv4)
        return self._init_connection(host, port)

    def _init_connection(self, host, port):
        """
        @param host: host to connect to
        @type host: str
        @param port: port to connect on
        @type port: int
        @return: HTTPConnection object
        """
        return LVWSHTTPConnection(host, port)

    def close(self):
        if self._connection:
            self._connection.close()

    def reconnect(self):
        """
        Internal convenience to reconnect using stored (host, port).
        """
        self._connection.close()
        self._connection.connect()

    def setip(self, ipv4):
        """
        @param ipv4: ipv4 address
        @type ipv4: str
        @return: None
        @rtype: None

        User responsible for making sure they didn't screw up the ipv4.
        Set internal ip address
        """
        if ipv4 == self._ipv4:
            return
        self.close()
        self._urlbase = self._url_template % ipv4
        self._ipv4 = ipv4
        self._host, self._port = self._parse_ipv4(ipv4)
        self._connection = self._init_connection(self._host, self._port)
        self._logger.name = self._calc_logger_name(ipv4)

    def request_from_call_and_args(self, call, args=()):
        """
        same as below, but 'call' is a separate argument
        """
        if args:
            query = ''.join(("?&call=", call, "&", "&".join("%s=%s" % a for a in args)))
        else:
            query = "?&call=" + call
        return self.send_request(query)

    def request_from_kwargs(self, **kwargs):
        query = "?" + "&".join("%s=%s" % item for item in kwargs.items())
        return self.send_request(query)

    def request_from_args(self, args):
        """
        @param args: tuple of (key, value) pairs to build a query string
        @type args: (T, T)
        @return: http.client.HTTPResponse
        @rtype: http.client.HTTPResponse

        Convenience for building a query string and calling hello.
        Intended for low-level public access.
        """

        query = "?&" + "&".join("=".join(a) for a in args)
        return self.send_request(query)

    def _do_request(self, url):
        nattempts = 1
        while True:
            try:
                rsp = self._connection.do_request('GET', url, None, self.headers)
            except (ConnectionAbortedError, BadStatusLine):
                if self.retry_count:
                    if nattempts > self.retry_count:
                        raise
            except Exception:
                # debug. eventually all connection quirks should be worked out
                # and handled appropriately.
                import traceback

                self._warn("=====================================")
                self._warn("UNKNOWN ERROR OCCURRED DURING REQUEST")
                self._warn("IPV4 ADDRESS:", self._ipv4)
                self._warn("REQUESTED URL: <%s>" % url)
                self._warn("=====================================")
                self._warn(traceback.format_exc())
                if self.retry_count:
                    if nattempts > self.retry_count:
                        raise
                    else:
                        nattempts += 1
                self.reconnect()
            else:
                return rsp

    def send_request(self, query):
        """
        @param query: query string to call hello ("?&call=....")
        @type query: str
        @return: http response object
        @rtype: http.client.HTTPResponse

        Call hello using the provided query string.
        Query string must be built explicitly.
        """
        url = self._urlbase + query
        rsp = self._do_request(url)

        cookie = rsp.headers.get("Set-Cookie")
        if cookie:
            self.headers['Cookie'] = cookie.split(';', 1)[0]
        return rsp

    def _do_set_validate(self, rsp):
        """
        Quickly validate that a set call returned a successful response.
        """
        root = self._parse_rsp(rsp)
        result = root[0]
        if not result.text == "True":
            raise ServerCallError(root[1].text)
        return True


class HelloApp(BaseHelloApp):

    def login(self, user='user1', pwd='12345'):
        query = "?&call=login&val1=%s&val2=%s&loader=Authenticating...&skipValidate=true" % (user, pwd)
        rsp = self.send_request(query)
        return self._do_set_validate(rsp)

    def logout(self):
        query = "?&call=logout"
        rsp = self.send_request(query)
        return self._do_set_validate(rsp)

    def startbatch(self, name):
        query = "?&call=setStartBatch&val1=%s" % name
        rsp = self.send_request(query)
        return self._do_set_validate(rsp)

    def endbatch(self):
        query = "?&call=setendbatch"
        rsp = self.send_request(query)
        return self._do_set_validate(rsp)

    def getAlarms(self, mode='first', val1='100', val2='1', loader="Loading+alarms..."):

        if loader:
            query = "?&call=getAlarms&mode=%s&val1=%s&val2=%s&loader=%s" % (mode, val1, val2, loader)
        else:
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

        # Not a parsing bug. the name of the cluster is "cluster". 
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
        # not sure what timeout does
        query = "?&call=getReport&mode=%s&type=%s&val1=%s&val2=%s&timeout=%s" % \
                (mode, type, val1, val2, timeout)
        rsp = self.send_request(query)
        xml = HelloXML(rsp)
        if not xml.result:
            raise ServerCallError(xml.data)
        return xml.data

    def getBatches(self):
        query = "?&call=getBatches&loader=Loading+batches..."
        rsp = self.send_request(query)
        xml = BatchListXML(rsp)
        if not xml.result:
            raise ServerCallError(xml.data)
        return xml

    def getreport_byname(self, type, name):
        return self.getReport('byBatch', type, name)

    def getdatareport_bybatchid(self, val1):
        fname = self.getReport('byBatch', 'Data', val1)
        url = "/reports/" + fname
        rsp2 = self._do_request(url)
        return rsp2.read()

    def getdatareport_bybatchname(self, name):
        query = "?&call=getBatches&loader=Loading+batches..."
        rsp = self.send_request(query)
        xml = BatchListXML(rsp)
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
        return self._do_set_validate(rsp)

    def setph(self, mode, co2, base=None):
        # Val1 = CO2 sp (or auto sp)
        # Val2 = base sp (unused if auto mode)
        if base is None:
            query = "?&call=set&group=ph&mode=%s&val1=%s" % (mode, co2)
        else:
            query = "?&call=set&group=ph&mode=%s&val1=%s&val2=%s" % (mode, co2, base)
        rsp = self.send_request(query)
        return self._do_set_validate(rsp)

    def setmg(self, mode, val):
        query = "?&call=set&group=maingas&mode=%s&val1=%s" % (mode, val)
        rsp = self.send_request(query)
        return self._do_set_validate(rsp)

    def setag(self, mode, val):
        query = "?&call=set&group=agitation&mode=%s&val1=%s" % (mode, val)
        rsp = self.send_request(query)
        return self._do_set_validate(rsp)

    def settemp(self, mode, val):
        query = "?&call=set&group=temperature&mode=%s&val1=%s" % (mode, val)
        rsp = self.send_request(query)
        return self._do_set_validate(rsp)

    def set_mode(self, group, mode, val):
        query = "?&call=set&group=%s&mode=%s&val1=%s" % (group, mode, val)
        rsp = self.send_request(query)
        return self._do_set_validate(rsp.read())

    def getDORAValues(self):
        query = "?&call=getDORAValues"
        rsp = self.send_request(query)
        xml = HelloXML(rsp)

        # Get dora values ends up returning a blank element
        # for the name of the cluster, so the dict ends up
        # being {None: DoraValues}
        if not xml.result:
            raise ServerCallError(xml.msg)
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
        return mv['message']

    # backward compatibility
    gmv = getMainValues
    gpmv = getMainValues

    def getAdvancedValues(self):
        query = "?&call=getAdvancedValues"
        rsp = self.send_request(query)
        xml = HelloXML(rsp)
        if not xml.result:
            raise ServerCallError(xml.msg)
        return xml.data['Advanced Values']

    # backward compatibility
    getadvv = getAdvancedValues

    def setconfig(self, group, name, val):
        name = sanitize_url(name)
        query = "?&call=setconfig&group=%s&name=%s&val=%s" % (group, name, str(val))
        rsp = self.send_request(query)
        return self._do_set_validate(rsp)

    def trycal(self, sensor, val1, target1, val2=None, target2=None):
        """
        @param sensor: sensor: "doa", "dob", "pha", "phb", "level", "pressure"
        @param val1: value returned by getRawValue()
        @param target1: pv that val1 actually corresponds to (value entered by user)
        @param val2: value returend by getRawValue()
        @param target2: pv that val1 actually corresponds to (value entered by user)
        """
        if val2 is None or target2 is None:
            # two point cal
            query = "?&call=trycal&sensor=%s&val1=%s&target1=%s&val2=%s&target2=%s" % (sensor, val1, target1,
                                                                                       val2, target2)
        else:
            # one point cal
            query = "?&call=trycal&sensor=%s&val1=%s&target1=%s" % (sensor, val1, target1)

        rsp = self.send_request(query)
        return self._do_set_validate(rsp)

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

    def getmodelsize(self):
        return int(self.getVersion()['Model'][4:])

    # Convenience functions

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
        if not xml.result:
            raise ServerCallError(xml.msg)

        # apparently Hello works just fine with either
        # of these, so the server can send back either one
        # check here so that we return the correct key. 
        try:
            return xml.data['System Variables']
        except KeyError:
            return xml.data['System_Variables']

    gpcfg = getConfig

    def getRecipes(self, loader="Loading+recipes"):
        query = "?&call=getRecipes&loader=" + loader
        rsp = self.send_request(query)
        xml = HelloXML(rsp)
        if not xml.result:
            raise ServerCallError(xml.msg)
        return xml.data.split(",")

    # repl support

    def __repr__(self):
        base = super().__repr__()
        return ' '.join((base, 'ipv4', self._ipv4))

    __str__ = __repr__

    def __getstate__(self):
        d = self.__dict__.copy()
        del d['_connection']
        return d

    def __setstate__(self, state):
        for k, v in state.items():
            setattr(self, k, v)
        self._connection = self._init_connection(self._host, self._port)


class HelloXML():

    def __init__(self, xml):
        if isinstance(xml, str):
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
            'Boolean': self.parse_bool
        }

    def _init(self, root):
        self._parsed = False

        # begin
        data = self.begin_parse(root)
        self.parse_dict = data['Reply']
        self.result = self.parse_dict['Result'] == 'True'
        self.data = self.msg = self.parse_dict['Message']

        if self.msg == 'True':
            raise TrueError("Expected response, got \"True\"")

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

        self.start_time = int(start_time)
        if stop_time == 'None':
            stop_time = None
        stop_time = int(stop_time or time())
        if stop_time - self.start_time < 0:
            stop_time = 2 ** 31 - 1  # epoch
        self.stop_time = stop_time

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

    def _get_parse_types(self):
        rv = HelloXML._get_parse_types(self)
        rv['Array'] = types.MethodType(HelloXML.parse_cluster, self)
        return rv

    def _init(self, root):

        self._parsed = False
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
            # Newer names are overridden with older names,
            # where 'newer' means 'higher id'
            names_to_batches = {}
            for entry in ids_to_batches.values():
                name = entry["Name"]
                id = entry['ID']
                if name in names_to_batches:
                    if id > names_to_batches[name]['ID']:
                        names_to_batches[name] = entry
                else:
                    names_to_batches[name] = entry

            self.names_to_batches = names_to_batches
            self.ids_to_batches = self.data = OrderedDict(sorted(ids_to_batches.items()))

            self._parsed = True
        else:
            self.names_to_batches = self.ids_to_batches = None
            self.data = self.reply['Message']

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
