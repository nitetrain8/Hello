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


class BadError(Exception):
    """ Encompases all things bad. """
    pass


class HelloError(BadError):
    """ Problem with Hello app class. """
    pass


class ServerCallError(HelloError):
    pass


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


class HelloApp():

    _headers = {}
    _url_template = "http://%s/webservice/interface/"

    def __init__(self, ipv4, headers=None):
        self._ipv4 = ipv4
        self._urlbase = "/webservice/interface/"

        self._host, self._port = self._parse_ipv4(ipv4)
        self._connection = self._init_connection(self._host, self._port)

        # create instance copy
        self.headers = self._headers.copy()
        if headers is not None:
            self.headers.update(headers)

        self._parse_rsp = parse_rsp

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
        c = HTTPConnection(host, port)
        return c

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
        self._urlbase = self._url_template % ipv4
        self._ipv4 = ipv4
        self._host, self._port = self._parse_ipv4(ipv4)
        self._connection = self._init_connection(self._host, self._port)

    def call_hello_from_args2(self, call, args=()):
        """
        same as below, but 'call' is a separate argument
        """
        query = ''.join(("?&call=", call, "&", "&".join("=".join(a) for a in args)))
        return self.call_hello(query)

    def call_hello_from_args(self, args):
        """
        @param args: tuple of (key, value) pairs to build a query string
        @type args: (T, T)
        @return: http.client.HTTPResponse
        @rtype: http.client.HTTPResponse

        Convenience for building a query string and calling hello.
        Intended for low-level public access.
        """

        query = "?&" + "&".join("=".join(a) for a in args)
        return self.call_hello(query)

    def _do_request(self, url):
        nattempts = 1
        retrycount = 3
        while True:
            try:
                self._connection.request('GET', url, None, self.headers)
                rsp = self._connection.getresponse()
            except (ConnectionAbortedError, BadStatusLine):
                if nattempts > retrycount:
                    raise
            except Exception:
                # debug. eventually all connection quirks should be worked out
                # and handled appropriately.
                import traceback
                print("=====================================")
                print("UNKNOWN ERROR OCCURRED DURING REQUEST")
                print("IPV4 ADDRESS:", self._ipv4)
                print("REQUESTED URL: <%s>" % url)
                print("=====================================")
                print(traceback.format_exc())
                if nattempts > retrycount:
                    raise
            else:
                return rsp
            nattempts += 1
            self.reconnect()

    def call_hello(self, query):
        """
        @param query: query string to call hello ("?&cal=....")
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

    def login(self, user='user1', pwd='12345'):
        query = "?&call=login&val1=%s&val2=%s&loader=Authenticating...&skipValidate=true" % (user, pwd)
        rsp = self.call_hello(query)
        return self._do_set_validate(rsp)

    def logout(self):
        query = "?&call=logout"
        rsp = self.call_hello(query)
        return self._do_set_validate(rsp)

    def _do_set_validate(self, rsp):
        # this is faster than calling HelloXML instance
        root = self._parse_rsp(rsp)
        result = root[0]
        if not result.text == "True":
            raise ServerCallError(root[1].text)
        return True

    def startbatch(self, name):
        query = "?&call=setStartBatch&val1=%s" % name
        rsp = self.call_hello(query)
        return self._do_set_validate(rsp)

    def endbatch(self):
        query = "?&call=setendbatch"
        rsp = self.call_hello(query)
        return self._do_set_validate(rsp)

    def getAlarms(self, mode='first', val1='100', val2='1', loader="Loading+alarms..."):

        if loader:
            query = "?&call=getAlarms&mode=%s&val1=%s&val2=%s&loader=%s" % (mode, val1, val2, loader)
        else:
            query = "?&call=getAlarms&mode=%s&val1=%s&val2=%s" % (mode, val1, val2)
        rsp = self.call_hello(query)
        xml = HelloXML(rsp)
        if not xml.result:
            raise ServerCallError(xml.msg)
        return xml.data['Alarms']

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
        rsp = self.call_hello(query)
        xml = HelloXML(rsp)
        if not xml.result:
            raise ServerCallError(xml.data)
        return xml.data

    def getbatches(self):
        query = "?&call=getBatches&loader=Loading+batches..."
        rsp = self.call_hello(query)
        xml = BatchListXML(rsp)
        if not xml.result:
            raise ServerCallError

    def getreport_byname(self, type, val1):
        return self.getReport('byBatch', type, val1)

    def getdatareport_bybatchid(self, val1):
        fname = self.getReport('byBatch', 'Data', val1)
        url = "/reports/" + fname
        rsp2 = self._do_request(url)
        return rsp2.read()

    def getdatareport_bybatchname(self, name):
        query = "?&call=getBatches&loader=Loading+batches..."
        rsp = self.call_hello(query)
        xml = BatchListXML(rsp)
        try:
            id = xml.getbatchid(name)
        except KeyError:
            raise HelloError("Bad batch name given- batch not found: " + name) from None
        return self.getdatareport_bybatchid(id)

    def setdo(self, mode, n2, o2=0):
        # Val1 = N2 sp (or auto sp)
        # Val2 = O2 sp (unused if auto mode)
        query = "?&call=set&group=do&mode=%s&val1=%s&val2=%s" % (mode, n2, o2)
        rsp = self.call_hello(query)
        return self._do_set_validate(rsp)

    def setmg(self, mode, val):
        query = "?&call=set&group=maingas&mode=%s&val1=%s" % (mode, val)
        rsp = self.call_hello(query)
        return self._do_set_validate(rsp)

    def setag(self, mode, val):
        query = "?&call=set&group=agitation&mode=%s&val1=%s" % (mode, val)
        rsp = self.call_hello(query)
        return self._do_set_validate(rsp)

    def set_mode(self, group, mode, val):
        query = "?&call=set&group=%s&mode=%s&val1=%s" % (group, mode, val)
        rsp = self.call_hello(query)
        return self._do_set_validate(rsp.read())

    def getdoravalues(self):
        query = "?&call=getDORAValues"
        rsp = self.call_hello(query)
        xml = HelloXML(rsp)

        # Get dora values ends up returning a blank element
        # for the name of the cluster, so the dict ends up
        # being {None: DoraValues}
        if not xml.result:
            raise ServerCallError(xml.msg)
        return xml.data[None]

    def batchrunning(self):
        return self.getdoravalues()['Batch'] != '--'

    def reciperunning(self):
        return self.getdoravalues()['Sequence'] != 'Idle'

    def reactorname(self):
        return self.getdoravalues()['Machine Name']

    def getMainValues(self):
        query = "?&call=getMainValues&json=true"
        rsp = self.call_hello(query)
        mv = json_loads(rsp.read().decode('utf-8'))
        return mv['message']

    # backward compatibility
    gmv = getMainValues
    gpmv = getMainValues

    def getAdvancedValues(self):
        query = "?&call=getAdvancedValues"
        rsp = self.call_hello(query)
        xml = HelloXML(rsp)
        if not xml.result:
            raise ServerCallError(xml.msg)
        return xml.data['Advanced Values']

    # backward compatibility
    getadvv = getAdvancedValues

    def setconfig(self, group, name, val):
        name = sanitize_url(name)
        query = "?&call=setconfig&group=%s&name=%s&val=%s" % (group, name, str(val))
        rsp = self.call_hello(query)
        return self._do_set_validate(rsp)

    def trycal(self, sensor, val1, target1, val2=None, target2=None):
        if val2 is None or target2 is None:
            # two point cal
            query = "?&call=trycal&sensor=%s&val1=%s&target1=%s&val2=%s&target2=%s" % (sensor, val1, target1,
                                                                                       val2, target2)
        else:
            # one point cal
            query = "?&call=trycal&sensor=%s&val1=%s&target1=%s" % (sensor, val1, target1)

        rsp = self.call_hello(query)
        return self._do_set_validate(rsp)

    def getRawValue(self, sensor):
        query = "?&call=getRawValue&sensor=" + sensor
        rsp = self.call_hello(query)
        xml = HelloXML(rsp)
        if not xml.result:
            raise ServerCallError(xml.data)
        return float(xml.data)

    def getVersion(self):
        query = "?&call=getVersion"
        rsp = self.call_hello(query)
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
        rsp = self.call_hello(query)
        xml = HelloXML(rsp)
        if not xml.result:
            raise ServerCallError(xml.msg)
        return xml.data['System Variables']

    gpcfg = getConfig

    def getRecipes(self, loader="Loading+recipes"):
        query = "?&call=getRecipes&loader=" + loader
        rsp = self.call_hello(query)
        xml = HelloXML(rsp)
        if not xml.result:
            raise ServerCallError(xml.msg)
        return xml.data.split(",")

    def __repr__(self):
        base = super().__repr__()
        return ' '.join((base, 'ipv4', self._ipv4))

    __str__ = __repr__


class HelloXML():
    parse_readable = parse_rsp

    def __init__(self, xml):
        if isinstance(xml, str):
            root = parse_xml(xml)
        else:
            root = self.parse_readable(xml)

        self._parse_types = self._parse_types
        self._parsed = False

        # begin
        name, parsed = self.parse(root)
        self.parse_dict = {name: parsed}
        self.reply = parsed
        self.result = parsed['Result'] == 'True'
        self.data = self.msg = parsed['Message']
        self._parsed = True

    # probably unnecessary: access self.data directly
    def getdata(self):
        if self._parsed:
            return self.data
        else:
            raise BadError("No data!")

    def parse(self, e):
        name = e.tag
        children = list(e)
        if not children:
            return name, e.text
        val = self.parse_children(children)
        return name, val

    def parse_children(self, elems):
        """
        @param elems: elements
        @type elems: list[xml.etree.ElementTree.Element]
        """
        rv = {}
        get_parser = self._parse_types.get
        for c in elems:
            parser = get_parser(c.tag)
            if parser:
                # must pass parser self explicitly, as
                # parse types dict is created in class body
                # (before methods become bound).
                k, v = parser(self, c)
            else:
                k, v = self.parse(c)
            rv[k] = v
        return rv

    def parse_int(self, e):
        name = e[0].text
        val = e[1].text
        val = int(val)
        return name, val

    def parse_bool(self, e):
        name = e[0].text
        val = e[1].text
        val = bool(val)
        return name, val

    def parse_string(self, e):
        name = e[0].text
        val = e[1].text
        val = str(val)
        return name, val

    def parse_float(self, e):
        name = e[0].text
        val = e[1].text
        val = float(val)
        return name, val

    def parse_cluster(self, e):
        name = e[0].text
        val = self.parse_children(e[2:])
        return name, val

    _parse_types = {
        'DBL': parse_float,
        'I32': parse_int,
        'I16': parse_int,
        'U16': parse_int,
        'U8': parse_int,
        'Cluster': parse_cluster,
        'String': parse_string,
        'Boolean': parse_bool
    }


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


class BatchListXML():
    """ The xml from getBatches is stupid and needs
    a different parsing scheme, and its own class.
    """
    def __init__(self, xml):
        root = parse_rsp(xml)

        self._parse_types = self._parse_types
        self._parsed = False
        name, parsed = self.parse(root)
        self.parse_dict = {name: parsed}
        self.reply = parsed
        self.result = parsed['Result'] == 'True'

        if self.result:
            ids_to_batches = parsed['Message']['Batches (cluster)']

            # map names <-> ids
            # note that many batches may have the same
            # newer names are overridden with older names,
            # where 'newer' means 'higher id'
            names_to_batches = {}
            for entry in ids_to_batches.values():
                entry_copy = entry.copy()
                name = entry_copy["Name"]
                id = entry_copy['ID']
                if name in names_to_batches:
                    if id > names_to_batches[name]['ID']:
                        names_to_batches[name] = entry_copy
                else:
                    names_to_batches[name] = entry_copy

            self.names_to_batches = names_to_batches
            self.ids_to_batches = self.data = OrderedDict(sorted(ids_to_batches.items()))

            self._parsed = True
        else:
            self.names_to_batches = self.ids_to_batches = None
            self.data = parsed['Message']

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

    def parse(self, e):
        name = e.tag
        children = list(e)
        if not children:
            return name, e.text
        val = self.parse_children(children)
        return name, val

    def parse_children(self, elems):
        """
        @param elems: elements
        @type elems: list[xml.etree.ElementTree.Element]
        """
        rv = {}
        get_parser = self._parse_types.get
        for c in elems:
            parser = get_parser(c.tag)
            if parser:
                # must pass parser self explicitly, as
                # parse types dict is created in class body
                # (before methods become bound).
                k, v = parser(self, c)
            else:
                k, v = self.parse(c)
            rv[k] = v
        return rv

    def parse_int(self, e):
        name = e[0].text
        val = e[1].text
        val = int(val)
        return name, val

    def parse_string(self, e):
        name = e[0].text
        val = e[1].text
        val = str(val)
        return name, val

    def parse_float(self, e):
        name = e[0].text
        val = e[1].text
        val = float(val)
        return name, val

    def parse_array(self, e):
        name = e[0].text
        val = self.parse_children(e[2:])
        return name, val

    def parse_batch(self, e):
        val = self.parse_children(e[2:])
        g = val.get  # brevity
        b = BatchEntry(g('ID'), g('Name'), g('Serial Number'), g('User'),
                       g('Start Time'), g('Stop Time'), g('Product Number'), g('Rev'))
        return b

    def parse_cluster(self, e):
        cname = e[0].text
        if cname == 'Batch':
            val = self.parse_batch(e)
        else:
            val = self.parse_children(e[2:])
        name = val['ID']
        return name, val

    def parse_bool(self, e):
        name = e[0].text
        val = e[1].text
        val = bool(val)
        return name, val

    _parse_types = {
        'DBL': parse_float,
        'I32': parse_int,
        'I16': parse_int,
        'U16': parse_int,
        'U8': parse_int,
        'Cluster': parse_cluster,
        'String': parse_string,
        'Array': parse_array,
        'Boolean': parse_bool
    }


def __test1():
    # noinspection PyUnusedLocal
    settings = (
        ("Agitation", "Minimum (RPM)", 3),
        ("Agitation", "Power Auto Max (%)", 100),
        ("Agitation", "Power Auto Min (%)", 3.9),
        ("Agitation", "Auto Max Startup (%)", 7),
        ("Agitation", "Samples To Average", 3),
        ("Agitation", "Min Mag Interval (s)", 0.1),
        ("Agitation", "Max Change Rate (%/s)", 100),
        ("Agitation", "PWM Period (us)", 1000),
        ("Agitation", "PWM OnTime (us)", 1000),
        ("Agitation", "P Gain  (%/RPM)", 3.5)
    )

    app = HelloApp('192.168.1.6')

    # for grp, setting, val in settings:
    # app.login()
    #     call = app.setconfig(grp, setting, val)
    #     print(sanitize_url(call))
    # app.login()

    i = 1
    from time import sleep, time

    start = time()
    while True:
        print("loop %d after %d seconds" % (i, time() - start))
        r, txt = app.setag(1, 10)
        print(r.getheaders())
        print(txt)
        i += 1
        sleep(1)


def __test2():
    b = HelloApp('192.168.1.6').getbatches()
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
    HelloApp('192.168.1.6').getdoravalues()

if __name__ == '__main__':
    __test5()
