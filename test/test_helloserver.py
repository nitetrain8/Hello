"""

Created by: Nathan Starkweather
Created on: 12/01/2014
Created in: PyCharm Community Edition

Module: test_module
Functions: test_functions

"""
import unittest
from os import makedirs
from os.path import dirname, join
from shutil import rmtree

__author__ = 'PBS Biotech'

test_dir = dirname(__file__)
temp_dir = join(test_dir, "temp")
test_input = join(test_dir, "test_input")
test_output = join(test_dir, "test_output")

def setUpModule():
    # Generate test input directory just in case
    # it doesn't already exist. (For Convenience).

    try:
        rmtree(test_output)
    except FileNotFoundError:
        pass

    for d in (temp_dir, test_input, test_output):
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
    from subprocess import Popen
    import os
    files = os.listdir(test_output)
    if files:
        files = ' '.join("\"%s\"" % join(test_output, f) for f in files)
        cmd = '"C:/Program Files/Notepad++/notepad++.exe" ' + files
        Popen(cmd)


from hello.mock.server import HelloServer, HelloState, HelloHTTPHandler
from http.client import HTTPConnection
from threading import Thread
from xml.etree.ElementTree import XML as parse_xml, Element, tostring as xml_tostring, ParseError
from json import loads as json_loads
from collections import OrderedDict
import sys


TEST_HOST = 'localhost'
TEST_PORT = 12345


def parse_json(s):
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    return json_loads(s)


def spawn_server_thread(server):
    thread = Thread(None, server.serve_forever)
    thread.daemon = True
    thread.start()
    return thread


def mock_pv_generator(val):
    def generator():
        while True:
            yield 1, val
    return generator().__next__


def dump_to_webbrowser(prefix, xml):
    import tempfile

    if isinstance(xml, Element):
        from hello.mock.debug_utils import simple_xml_dump_debug
        xml = simple_xml_dump_debug(xml)
    if isinstance(xml, str):
        mode = 'w'
    elif isinstance(xml, bytes):
        mode = 'wb'

        # prefix = prefix.encode('ascii')

    else:
        raise ValueError("Can't dump object of type %s" % xml.__class__.__name__)
    file = tempfile.NamedTemporaryFile(mode, prefix=prefix, suffix=".xml", delete=False, dir=test_output)
    file.write(xml)


def init_hello_state():
    s = HelloState()

    s.agitation.pv = 1
    s.agitation.sp = 2
    s.agitation.man = 3
    s.agitation.mode = 4
    s.agitation.error = 5
    s.agitation.interlocked = 6
    s.agitation.set_pvgen(mock_pv_generator(s.agitation.pv))

    s.temperature.pv = 46
    s.temperature.sp = 47
    s.temperature.man = 48
    s.temperature.mode = 49
    s.temperature.error = 50
    s.temperature.interlocked = 51
    s.temperature.set_pvgen(mock_pv_generator(s.temperature.pv))

    s.secondaryheat.pv = 40
    s.secondaryheat.sp = 41
    s.secondaryheat.man = 44
    s.secondaryheat.mode = 45
    s.secondaryheat.error = 42
    s.secondaryheat.interlocked = 43
    s.secondaryheat.set_pvgen(mock_pv_generator(s.secondaryheat.pv))

    s.do.pv = 7
    s.do.sp = 8
    s.do.manUp = 10
    s.do.manDown = 9
    s.do.mode = 11
    s.do.error = 12
    s.do.interlocked = 13
    s.do.set_pvgen(mock_pv_generator(s.do.pv))

    s.ph.pv = 29
    s.ph.sp = 30
    s.ph.manUp = 34
    s.ph.manDown = 33
    s.ph.mode = 35
    s.ph.error = 31
    s.ph.interlocked = 32
    s.ph.set_pvgen(mock_pv_generator(s.ph.pv))

    s.pressure.pv = 36
    s.pressure.sp = 37
    s.pressure.mode = 39
    s.pressure.error = 38
    s.pressure.set_pvgen(mock_pv_generator(s.pressure.pv))

    s.level.pv = 19
    s.level.sp = 20
    s.level.mode = 22
    s.level.error = 21
    s.level.set_pvgen(mock_pv_generator(s.level.pv))

    s.filteroven.pv = 14
    s.filteroven.sp = 15
    s.filteroven.mode = 17
    s.filteroven.error = 16
    s.filteroven.set_pvgen(mock_pv_generator(s.filteroven.pv))

    s.maingas.pv = 23
    s.maingas.sp = 24
    s.maingas.error = 25
    s.maingas.interlocked = 26
    s.maingas.man = 27
    s.maingas.mode = 28
    s.maingas.set_pvgen(mock_pv_generator(s.maingas.pv))

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


# noinspection PyAttributeOutsideInit
class HelloServerTestBase():

    handler_use_real_mode = False

    def setUp(self):
        """
        @type self: T >= unittest.TestCase
        """
        self.state = init_hello_state()
        self.server = HelloServer(TEST_HOST, TEST_PORT, self.state)
        self.thread = spawn_server_thread(self.server)
        self.connection = HTTPConnection(TEST_HOST, TEST_PORT)
        self.addTypeEqualityFunc(Element, self.assertXMLElementEqual)
        self.addTypeEqualityFunc(dict, self.assertMappingEqual)
        self.addTypeEqualityFunc(OrderedDict, self.assertMappingEqual)

        HelloHTTPHandler.real_mode = self.handler_use_real_mode

    def tearDown(self):
        self.server.shutdown()
        self.connection.close()
        assert not self.thread.is_alive()
        self.state = None
        self.server = None
        self.thread = None
        self.connection = None

    def assertMappingEqual(self, first, second, keychain=None, msg=None):
        """
        @type self: T >= unittest.TestCase
        """
        msg = msg or ""
        if keychain is None:
            keychain = []

        self.assertIsInstance(first, dict, "First argument is not a dict")
        self.assertIsInstance(second, dict, "Second argument is not a dict")

        fkeys = set(first)
        skeys = set(second)

        if fkeys != skeys:
            firstmsg = ", ".join(fkeys - skeys)
            secondmsg = ", ".join(skeys - fkeys)
            raise self.failureException(msg + "Dict keys missing: "
                                              "\nFirst only: %s"
                                              "\nSecond only: %s"
                                              "\nKeychain: %s" % (firstmsg, secondmsg, ', '.join(keychain)))

        for key in fkeys:
            keychain.append(key)
            v1 = first[key]
            if isinstance(v1, dict):
                self.assertMappingEqual(v1, second[key], keychain, msg)
            else:
                self.assertEqual(v1, second[key], "Keychain: " + ", ".join(keychain))
            keychain.pop()

    def assertXMLElementEqual(self, expected, actual, msg=None):
        self.recursive_assert_xml_element_equal(expected, actual, [], msg or "")

    def fail_mismatch_elements(self, expected, actual, chain, msg):
        """
        @type self: T >= unittest.TestCase
        """
        try:
            siblings = ", ".join(''.join(("<", e.tag, ":", e.text or '', ">")) for e in chain[-1]
                                    if e not in (expected, actual))
        except IndexError:
            siblings = "None"
        msg += """
Element chain: %s
Siblings: %s
expected.tag: %r\t|actual.tag: %r
expected.text: %r\t|actual.text: %r
expected.attrib: %r\t|actual.attrib: %r
expected.tail: %r\t|actual.tail: %r
# expected children: %d\t|# actual children: %d
Expected Children: %s
Actual Children: %s""" % (
                            ", ".join(e.tag.join(("<", ">")) for e in chain),
                            siblings,
                            expected.tag, actual.tag,
                            expected.text, actual.text,
                            ', '.join("%s=%s" % i for i in expected.attrib), \
                            ', '.join("%s=%s" % i for i in actual.attrib),
                            expected.tail, actual.tail,
                            len(expected), len(actual),
                            ", ".join(e.tag.join(("<", ">")) for e in expected),
                            ", ".join(a.tag.join(("<", ">")) for a in actual)
                            )
        raise self.failureException(msg)

    def recursive_assert_xml_element_equal(self, expected, actual, chain, msg):
        """
        @type self: T >= unittest.TestCase
        """
        self.assertIsInstance(expected, Element, msg + "First argument is not an Element")
        self.assertIsInstance(actual, Element, msg + "First argument is not an Element")

        if expected.tag != actual.tag or \
            expected.text != actual.text or \
            expected.attrib != actual.attrib or \
            expected.tail != actual.tail or len(expected) != len(actual):

            self.fail_mismatch_elements(expected, actual, chain, msg)

        chain.append(expected)
        for f, s in zip(expected, actual):
            self.recursive_assert_xml_element_equal(f, s, chain, msg)
        chain.pop()

    def basic_query(self, call, params=None):
        query = "/webservice/interface/?&call=" + call
        if params:
            query += "&" + "&".join("%s=%s" % p for p in params)
        self.connection.request("GET", query)
        rsp = self.connection.getresponse()
        return rsp, rsp.read()

    def maybe_got_xml_instead_of_json(self, doc):
        try:
            parse_xml(doc)
        except ParseError:
            return False
        else:
            return True

    def maybe_got_json_instead_of_xml(self, doc):
        try:
            parse_json(doc)
        except ValueError:
            return False
        else:
            return True

    def do_test_expect_json(self, call, params, rawname=None):
        """
         @type self: T >= unittest.TestCase
        """
        if rawname is None:
            rawname = call + ".json"
        expected_json_doc = load_test_input(rawname)
        expected_dict = parse_json(expected_json_doc)
        rsp, actual_json_doc = self.basic_query(call, params)
        actual_json_doc = actual_json_doc.decode()
        try:
            actual_dict = parse_json(actual_json_doc)
        except ValueError:
            # bad json. Check if we got an xml reply by mistake
            if self.maybe_got_xml_instead_of_json(actual_json_doc):
                raise self.failureException("Got wrong document type (expected json): %s" % actual_json_doc) from None
            raise

        self.assertEqual(expected_dict, actual_dict)
        try:
            self.assertEqual(expected_json_doc, actual_json_doc)
        except:
            print("EXPECTED (%d chars):" % len(expected_json_doc), file=sys.stderr)
            print(expected_json_doc, file=sys.stderr)
            print("GOT (%d chars):" % len(actual_json_doc), file=sys.stderr)
            print(actual_json_doc, file=sys.stderr)
            raise

    def do_test_expect_xml(self, call, params, rawname=None):
        """
         @type self: T >= unittest.TestCase
        """
        if rawname is None:
            rawname = call + ".xml"
        if not rawname.endswith(".xml"):
            rawname += ".xml"
        expected_xml_doc = load_test_input(rawname)
        expected_tree = parse_xml(expected_xml_doc)
        rsp, actual_xml_doc = self.basic_query(call, params)
        try:
            actual_tree = parse_xml(actual_xml_doc)
        except ValueError:
            # bad xml. Check if we got an xml reply by mistake
            if self.maybe_got_xml_instead_of_xml(actual_xml_doc):
                raise self.failureException("Got wrong document type (expected xml): %s" % actual_xml_doc) from None
            raise

        try:
            self.assertEqual(expected_tree, actual_tree)
        except self.failureException:
            dump_to_webbrowser('expected ' + call, expected_tree)
            dump_to_webbrowser('actual ' + call, actual_tree)
            raise
        try:
            self.assertEqual(expected_xml_doc, actual_xml_doc)
        except:
            print("EXPECTED (%d chars):" % len(expected_xml_doc), file=sys.stderr)
            print(expected_xml_doc, file=sys.stderr)
            print("GOT (%d chars):" % len(actual_xml_doc), file=sys.stderr)
            print(actual_xml_doc, file=sys.stderr)
            raise


class TestGetMainValues(HelloServerTestBase, unittest.TestCase):
    def test_xml1(self):
        """
        Basic call. No parameters.
        """

        call = 'getMainValues'
        params = ()
        self.do_test_expect_xml(call, params)

    def test_xml2(self):
        """
        Basic call. Json = False.
        """
        call = 'getMainValues'
        params = (
            ('json', 'False'),
        )
        self.do_test_expect_xml(call, params)

    def test_xml3(self):
        """
        Basic call. Json = 0.
        """

        call = 'getMainValues'
        params = (
            ('json', '0'),
        )
        self.do_test_expect_xml(call, params)

    def test_xml4(self):
        """
        Basic call. No parameters.
        """

        call = 'getMainValues'.lower()
        params = ()
        self.do_test_expect_xml(call, params, 'getMainValues.xml')

    def test_foobar_xml1(self):
        """
        Basic call. No parameters.
        """

        call = 'getMainValues'
        params = (
            ("Foo", "Bar"),
        )
        self.do_test_expect_xml(call, params, 'getMainValues_bad_foobar.xml')

    def test_json1(self):
        call = 'getMainValues'
        params = (
            ('json', 'True'),
        )
        self.do_test_expect_json(call, params)

    def test_json2(self):
        call = 'getMainValues'
        params = (
            ('json', '1'),
        )
        self.do_test_expect_json(call, params)

    def test_json3(self):
        call = 'getMainValues'.lower()
        params = (
            ('json', 'True'),
        )
        self.do_test_expect_json(call, params, 'getMainValues.json')

    def test_foobar_json1(self):
        call = 'getMainValues'
        params = (
            ('json', '1'),
            ('Foo', 'Bar')
        )
        self.do_test_expect_json(call, params, 'getMainValues_bad_foobar.json')


class TestLogin(HelloServerTestBase, unittest.TestCase):

    def test_login_xml1(self):
        call = 'login'
        params = (
            ("val1", "user1"),
            ("val2", "12345"),
            ("loader", "Authenticating"),
            ("skipValidate", "True")
        )

        self.do_test_expect_xml(call, params)

    def test_login_xml2(self):
        call = 'login'
        params = (
            ("val1", "pbstech"),
            ("val2", "727246"),
            ("loader", "Authenticating"),
            ("skipValidate", "True")
        )

        self.do_test_expect_xml(call, params)

    def test_login_xml3(self):
        call = 'login'
        params = (
            ("val1", "pbstech"),
            ("val2", "727246")
        )

        self.do_test_expect_xml(call, params)

    def test_login_xml4(self):
        call = 'login'
        params = (
            ("val1", "user1"),
            ("val2", "12345")
        )

        self.do_test_expect_xml(call, params)

    def test_login_failure_xml1(self):
        call = 'login'
        params = (
            ("val1", "bad"),
            ("val2", "81972")
        )

        self.do_test_expect_xml(call, params, 'login_bad.xml')

    def test_login_failure_xml2(self):
        call = 'login'
        params = (
            ("val1", ""),
            ("val2", "")
        )

        self.do_test_expect_xml(call, params, 'login_bad.xml')

    def test_login_failure_xml3(self):
        call = 'login'
        params = ()

        self.do_test_expect_xml(call, params, 'login_bad.xml')

    def test_login_json1(self):
        call = 'login'
        params = (
            ("val1", "user1"),
            ("val2", "12345"),
            ("loader", "Authenticating"),
            ("skipValidate", "True")
        )

        self.do_test_expect_json(call, params)

    def test_login_json2(self):
        call = 'login'
        params = (
            ("val1", "pbstech"),
            ("val2", "727246"),
            ("loader", "Authenticating"),
            ("skipValidate", "True")
        )

        self.do_test_expect_json(call, params)

    def test_login_json3(self):
        call = 'login'
        params = (
            ("val1", "pbstech"),
            ("val2", "727246")
        )

        self.do_test_expect_json(call, params)

    def test_login_json4(self):
        call = 'login'
        params = (
            ("val1", "user1"),
            ("val2", "12345")
        )

        self.do_test_expect_json(call, params)

    def test_login_failure_json1(self):
        call = 'login'
        params = (
            ("val1", "bad"),
            ("val2", "81972")
        )

        self.do_test_expect_json(call, params, "login_bad.json")

    def test_login_failure_json2(self):
        call = 'login'
        params = (
            ("val1", ""),
            ("val2", "")
        )

        self.do_test_expect_json(call, params, "login_bad.json")

    def test_login_failure_json3(self):
        call = 'login'
        params = ()

        self.do_test_expect_json(call, params, "login_bad.json")

    def test_login_failure_json4(self):
        call = 'login'
        params = (
            ("foo", "bar"),
        )

        self.do_test_expect_json(call, params, "login_bad.json")

    def test_login_failure_xml4(self):
        call = 'login'
        params = (
            ("foo", "bar"),
        )

        self.do_test_expect_xml(call, params, "login_bad.xml")


if __name__ == '__main__':
    unittest.main()
