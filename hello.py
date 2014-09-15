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


class HelloError(Exception):
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



