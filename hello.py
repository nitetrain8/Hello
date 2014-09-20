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


class BadError(Exception):
    pass


class HelloError(BadError):
    pass


class AuthError(HelloError):
    pass


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

        User is making sure they didn't screw up the ipv4
        """
        self.ipv4 = ipv4
        self.urlbase = self._url_template % ipv4

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

    def validate_rsp(self, xml):
        root = parse_xml(xml)
        msg = root[1]
        return msg.text == "True"

    def setag(self, mode, val):
        url = self.urlbase + "call=set&group=agitation&mode=%s&val1=%f" % (mode, val)
        return self.call_hello(url)

    def getMainValues(self):
        url = self.urlbase + "call=getMainValues&json=true"
        return self.call_hello(url)

    gmv = getMainValues

    def parsemv(self, mv):
        return loads(mv.read().decode('utf-8'))

    def gpmv(self):
        return self.parsemv(self.getMainValues())['message']

    def setconfig(self, group, name, val):
        name = name.replace("_", "__").replace(" ", "_")
        url = self.urlbase + "call=setconfig&group=%s&name=%s&val=%s" \
                             % (group, name, str(val))
        rsp = self.call_hello(url)
        txt = rsp.read().decode('utf-8')
        if not self.validate_rsp(txt):
            raise AuthError(txt)

    def getagpv(self):
        return self.gpmv()['agitation']['pv']

    def getconfig(self):
        url = self.urlbase + "call=getconfig"
        return self.call_hello(url)

    def parseconfig(self, rsp):
        # Rsp is the return from getconfig
        cfg = ConfigXML(rsp.read())
        return cfg

    def gpcfg(self):
        return self.parseconfig(self.getconfig())


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
    so this is a quick override to return a more convenient
    mapping.
    """
    def getdata(self):
        if self._parsed:
            return self.data['System_Variables']
        else:
            raise BadError("Oh No, no Data!")


if __name__ == '__main__':
    print(HelloApp('192.168.1.6').gpcfg().data)
