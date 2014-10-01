"""

Created by: Nathan Starkweather
Created on: 09/11/2014
Created in: PyCharm Community Edition

General purpose module for making REPL friendly
hello functions and such. Compile some common functions
from other modules/ipython sessions/etc.

Maybe turn into __init__.py?
"""

__author__ = 'Nathan Starkweather'

from urllib.request import urlopen, Request
from xml.etree.ElementTree import XML as parse_xml
from json import loads
from re import compile as re_compile


class BadError(Exception):
    """ Encompases all things bad. """
    pass


class HelloError(BadError):
    """ Problem with Hello app class. """
    pass


class AuthError(HelloError):
    """ Authentication Error. Most likely due to
    failure to properly maintain state across multiple
    server calls.
    """
    pass


class XMLError(HelloError):
    """ Problem with XML returned from a server call """
    pass


_sanitize = re_compile(r"([\s:%/])").sub

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


def sanitize_url(call):
    return _sanitize(_sanitize_cb, call)


class HelloApp():

    _headers = {}
    _url_template = "http://%s/webservice/interface/?&"

    def __init__(self, ipv4, headers=None):
        self.ipv4 = ipv4
        self.urlbase = self._url_template % ipv4

        # create instance copy
        self.headers = self._headers.copy()
        if headers is not None:
            self.headers.update(headers)

    def setip(self, ipv4):
        """
        @param ipv4: ipv4 address
        @type ipv4: str
        @return: None
        @rtype: None

        User responsible for making sure they didn't screw up the ipv4
        """
        self.urlbase = self._url_template % ipv4
        self.ipv4 = ipv4

    def call_hello(self, url):

        req = Request(url, headers=self.headers)
        rsp = urlopen(req)
        rhdrs = rsp.getheaders()
        for h, v in rhdrs:
            if h == 'Set-Cookie':
                self.headers['Cookie'] = v.split(';', 1)[0]
        return rsp

    def login(self, user='user1', pwd='12345'):
        url = self.urlbase + "call=login&val1=%s&val2=%s&loader=Authenticating...&skipValidate=true" % (user, pwd)
        rsp = self.call_hello(url)
        txt = rsp.read().decode('utf-8')
        root = parse_xml(txt)
        msg = root[1]
        if msg.text != "True":
            raise AuthError("Bad login " + msg.text)
        return rsp

    def validate_set_rsp(self, xml):
        root = parse_xml(xml)
        msg = root[1]
        return msg.text == "True"

    def setag(self, mode, val):
        url = self.urlbase + "call=set&group=agitation&mode=%s&val1=%f" % (mode, val)
        rsp = self.call_hello(url)
        return self.validate_set_rsp(rsp.read())

    def getMainValues(self):
        url = self.urlbase + "call=getMainValues&json=true"
        return self.call_hello(url)

    gmv = getMainValues

    def parsemv(self, mv):
        return loads(mv.read().decode('utf-8'))

    def gpmv(self):
        return self.parsemv(self.getMainValues())['message']

    def setconfig(self, group, name, val):
        if ':' in name:
            name = name.replace(":", "")
        if ' ' in name:
            name = name.replace(" ", "_")

        call = "call=setconfig&group=%s&name=%s&val=%s" % (group, name, str(val))
        url = self.urlbase + sanitize_url(call)
        rsp = self.call_hello(url)
        txt = rsp.read().decode('utf-8')
        if not self.validate_set_rsp(txt):
            raise AuthError(txt)

    def getagpv(self):
        return float(self.gpmv()['agitation']['pv'])

    def getautoagvals(self):
        mv = self.gpmv()
        ag = mv['agitation']
        return ag['pv'], ag['sp']

    def getmanagvals(self):
        mv = self.gpmv()
        ag = mv['agitation']
        return ag['pv'], ag['man']

    def getconfig(self):
        url = self.urlbase + "call=getconfig"
        return self.call_hello(url)

    def parseconfig(self, rsp):
        # Rsp is the return from getconfig
        cfg = ConfigXML(rsp.read())
        return cfg

    def gpcfg(self):
        return self.parseconfig(self.getconfig())

    def __repr__(self):
        base = super().__repr__()
        return ' '.join((base, 'ipv4', self.ipv4))

    __str__ = __repr__


class HelloXML():

    def __init__(self, xml):
        root = parse_xml(xml)

        self._parse_types = {
            'DBL': self.parse_float,
            'I32': self.parse_int,
            'I16': self.parse_int,
            'U16': self.parse_int,
            'U8': self.parse_int,
            'Cluster': self.parse_cluster
        }

        self._parsed = False
        name, parsed = self.parse(root)
        self.parse_dict = {name: parsed}
        self.reply = parsed
        self.result = parsed['Result']
        self.data = parsed['Message']
        self._parsed = True

    def getdata(self):
        if self._parsed:
            return self.data
        else:
            raise BadError("No data!")

    def getresult(self):
        if self._parsed:
            return self.data
        else:
            raise BadError("No result!")

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
            ctag = c.tag
            parser = get_parser(ctag)
            if parser is None:
                k, v = self.parse(c)
            else:
                k, v = parser(c)
            rv[k] = v
        return rv

    def parse_int(self, e):
        name = e[0].text
        val = e[1].text
        val = int(val)
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


class ConfigXML(HelloXML):
    """ getconfig sends back kind of a weird xml
    so this is a quick override of super's method to return
    a more convenient mapping.
    """
    def getdata(self):
        if self._parsed:
            return self.data['System_Variables']
        else:
            raise XMLError("Oh No, no Data!")


if __name__ == '__main__':
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

    for grp, setting, val in settings:
        app.login()
        call = app.setconfig(grp, setting, val)
        print(sanitize_url(call))
