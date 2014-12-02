"""

Created by: Nathan Starkweather
Created on: 12/01/2014
Created in: PyCharm Community Edition

Module: test_module
Functions: test_functions

"""
import unittest
from os import makedirs
from os.path import dirname, join, exists
from shutil import rmtree

__author__ = 'PBS Biotech'

test_dir = dirname(__file__)
temp_dir = join(test_dir, "temp")
test_input = join(test_dir, "test_input")


def setUpModule():
    # Generate test input directory just in case
    # it doesn't already exist. (For Convenience). 
    for d in (temp_dir, test_input):
        try:
            makedirs(d)
        except FileExistsError:
            pass


def tearDownModule():
    # Don't remove test input!
    try:
        rmtree(temp_dir)
    except FileNotFoundError:
        pass


from hello.mock.server import HelloServer, HelloState
from http.client import HTTPConnection
from threading import Thread
from xml.etree.ElementTree import XML as parse_xml, Element
from itertools import zip_longest
from json import dumps as json_dumps, loads as json_loads

TEST_HOST = 'localhost'
TEST_PORT = 12345


def spawn_server_thread(server):
    thread = Thread(None, server.serve_forever)
    thread.daemon = True
    thread.start()
    return thread


def init_hello_state():
    s = HelloState()
    s.agitation.error = 1
    s.agitation.interlocked = 2
    s.agitation.man = 3
    s.agitation.mode = 4
    s.agitation.pv = 5
    s.agitation.sp = 6
    s.do.error = 7
    s.do.interlocked = 8
    s.do.manDown = 9
    s.do.manUp = 10
    s.do.mode = 11
    s.do.pv = 12
    s.do.sp = 13
    s.filteroven.error = 14
    s.filteroven.mode = 15
    s.filteroven.pv = 16
    s.filteroven.sp = 17
    s.level.error = 18
    s.level.mode = 19
    s.level.pv = 20
    s.level.sp = 21
    s.maingas.error = 22
    s.maingas.interlocked = 23
    s.maingas.man = 24
    s.maingas.mode = 25
    s.maingas.pv = 26
    s.maingas.sp = 27
    s.ph.error = 28
    s.ph.interlocked = 29
    s.ph.manDown = 30
    s.ph.manUp = 31
    s.ph.mode = 32
    s.ph.pv = 33
    s.ph.sp = 34
    s.pressure.error = 35
    s.pressure.mode = 36
    s.pressure.pv = 37
    s.pressure.sp = 38
    s.secondaryheat.error = 39
    s.secondaryheat.interlocked = 40
    s.secondaryheat.man = 41
    s.secondaryheat.mode = 42
    s.secondaryheat.pv = 43
    s.secondaryheat.sp = 44
    s.temperature.error = 45
    s.temperature.interlocked = 46
    s.temperature.man = 47
    s.temperature.mode = 48
    s.temperature.pv = 49
    s.temperature.sp = 50

    return s


def load_test_input(name):
    json = name.endswith(".json")
    if json:
        mode = 'r'
    else:
        mode = 'rb'
    pth = join(test_input, name)
    with open(pth, mode) as f:
        contents = f.read()
    return contents


class TestHelloServer(unittest.TestCase):

    def setUp(self):
        self.state = init_hello_state()
        self.server = HelloServer(TEST_HOST, TEST_PORT, self.state)
        self.thread = spawn_server_thread(self.server)
        self.connection = HTTPConnection(TEST_HOST, TEST_PORT)
        self.addTypeEqualityFunc(Element, self.assertXMLElementEqual)

    def tearDown(self):
        self.server.shutdown()
        assert not self.thread.is_alive()
        self.state = None
        self.server = None
        self.thread = None
        
    def assertXMLElementEqual(self, first, second, msg=None):

        self.assertIsInstance(first, Element, "First argument is not an Element")
        self.assertIsInstance(second, Element, "First argument is not an Element")

        self.assertEqual(first.tag, second.tag)
        self.assertEqual(first.text, second.text)
        self.assertEqual(first.attrib, second.attrib)
        self.assertEqual(first.tail, second.tail)

        for f, s in zip_longest(first, second):
            self.assertXMLElementEqual(f, s, msg)

    def test_getmainvalues(self):
        """
        @return: None
        @rtype: None
        """

        expected_xml = load_test_input('getMainValues.xml')
        expected_tree = parse_xml(expected_xml)
        expected_json = load_test_input('getMainValues.json')
        expected_dict = json_loads(expected_json)

        # base call. expect XML document
        mv_xml = self.connection.request("GET", "/webservice/interface/?&call=getMainValues").read()
        mv_tree = parse_xml(mv_xml)

        self.assertEqual(expected_xml, mv_xml)
        self.assertEqual(expected_tree, mv_tree)

        #





if __name__ == '__main__':
    unittest.main()
