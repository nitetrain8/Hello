"""

Created by: Nathan Starkweather
Created on: 11/05/2014
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


from hello.mock.state import StandardController, TwoWayController, SmallController, HelloState
from hello.mock import state as hello_state
from json import loads as json_loads, dumps as json_dumps


class TestState(unittest.TestCase):

    def setUp(self):
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

        self.hello_state = s

    def test_get_dict_main_values(self):
        s = self.hello_state

        expected = {
            "result": "True",
            "message": {
                'Agitation': {
                    'error': 1,
                    'interlocked': 2,
                    'man': 3,
                    'mode': 4,
                    'pv': 5,
                    'sp': 6,
                },

                'DO': {
                    'error': 7,
                    'interlocked': 8,
                    'manDown': 9,
                    'manUp': 10,
                    'mode': 11,
                    'pv': 12,
                    'sp': 13,
                },

                'Condenser': {
                    'error': 14,
                    'mode': 15,
                    'pv': 16,

                },

                'Level': {
                    'error': 18,
                    'mode': 19,
                    'pv': 20,

                },

                'MainGas': {
                    'error': 22,
                    'interlocked': 23,
                    'man': 24,
                    'mode': 25,
                    'pv': 26,
                    'sp': 27,
                },

                'pH': {
                    'error': 28,
                    'interlocked': 29,
                    'manDown': 30,
                    'manUp': 31,
                    'mode': 32,
                    'pv': 33,
                    'sp': 34,
                },

                'Pressure': {
                    'error': 35,
                    'mode': 36,
                    'pv': 37,
                },

                'SecondaryHeat': {
                    'error': 39,
                    'interlocked': 40,
                    'man': 41,
                    'mode': 42,
                    'pv': 43,
                    'sp': 44,
                },

                'Temperature': {
                    'error': 45,
                    'interlocked': 46,
                    'man': 47,
                    'mode': 48,
                    'pv': 49,
                    'sp': 50,
                }
            }
        }

        actual = s.get_dict_main_values()

        try:
            self.assertEqual(expected, actual)
        except self.failureException:
            # the standard dict assert equal message sucks,
            # so if the test fails, loop manually here to get a
            # better error message
            self.assertEqual(set(expected.keys()), set(actual.keys()))
            emsg = expected['message']
            amsg = actual['message']
            try:
                self.assertEqual(set(emsg.keys()), set(amsg.keys()))
            except self.failureException:
                for key in emsg.keys():
                    self.assertIn(key, amsg)
                raise
            for ekey in emsg:
                self.assertIn(ekey, amsg)
                eval = emsg[ekey]
                aval = amsg[ekey]
                for ekey2 in eval:
                    self.assertIn(ekey2, aval)
                    eval2 = eval[ekey2]
                    aval2 = aval[ekey2]
                    self.assertEqual(eval2, aval2, " ".join((ekey, ekey2)))
            raise

        # these won't necessarily match, because dict order is arbitrary
        expected_json = json_dumps(expected)
        actual_json = json_dumps(actual)

        # loading the dump dict back should match, though
        expected_from_json = json_loads(expected_json)
        actual_from_json = json_loads(actual_json)

        self.assertEqual(expected_from_json, actual_from_json)


class ControllerTestBase():
    def setUp(self):
        self.controller = None

    def assertAllIn(self, keys, container, msg=None):
        diffs = []
        for key in keys:
            if key not in container:
                diffs.append(str(key))

        if diffs:
            msg2 = "Keys not in container: " + " ".join(diffs)
            if msg:
                msg2 += msg
            raise self.failureException(msg2)

    def assertHasAttrs(self, obj, attrs, msg=None):
        for a in attrs:
            if not hasattr(obj, a):
                raise self.failureException(str(a) + msg)

    def test_controller_mv_attrs(self):

        mv_attrs = self.controller.mv_attrs
        set_mv_attrs = set(mv_attrs)

        self.assertEqual(len(mv_attrs), len(set_mv_attrs))
        self.assertAllIn(mv_attrs, set_mv_attrs)
        self.assertHasAttrs(self.controller, mv_attrs)

    def test_controller_mi_attrs(self):
        mi_attrs = self.controller.mi_attrs
        set_mv_attrs = set(mi_attrs)

        self.assertEqual(len(mi_attrs), len(set_mv_attrs))
        self.assertAllIn(mi_attrs, set_mv_attrs)
        self.assertHasAttrs(self.controller, mi_attrs)


class TestSimpleController(ControllerTestBase, unittest.TestCase):

    def setUp(self):
        c = StandardController("TestSimpleController")
        c.pv = 1
        c.sp = 2
        c.man = 3
        c.mode = 4
        c.error = 5
        c.interlocked = 6

        self.controller = c

    def test_mv_todict(self):
        """
        @return: None
        @rtype: None
        """
        c = self.controller

        expected = {
            'pv': 1,
            'sp': 2,
            'man': 3,
            'mode': 4,
            'error': 5,
            'interlocked': 6
        }

        actual = c.mv_todict()

        self.assertEqual(expected, actual)


class TestTwoWayController(ControllerTestBase, unittest.TestCase):
    def setUp(self):
        c = TwoWayController("TestTwoWayController")
        c.pv = 1
        c.sp = 2
        c.manUp = 3
        c.manDown = 4
        c.mode = 5
        c.error = 6
        c.interlocked = 7
        self.controller = c

    def test_mvtodict(self):
        c = self.controller
        expected = {
            'pv': 1,
            'sp': 2,
            'manUp': 3,
            'manDown': 4,
            'mode': 5,
            'error': 6,
            'interlocked': 7
        }

        actual = c.mv_todict()

        self.assertEqual(expected, actual)


class TestSmallController(ControllerTestBase, unittest.TestCase):
    def setUp(self):
        c = SmallController("TestSmallController")
        c.pv = 1
        c.sp = 2
        c.mode = 3
        c.error = 4
        self.controller = c

    def test_mv_todict(self):

        c = self.controller
        expected = {
            'pv': 1,
            'mode': 3,
            'error': 4
        }

        actual = c.mv_todict()

        self.assertEqual(expected, actual)


class TestStateMainInfo(unittest.TestCase):

    def setUp(self):
        self.root_xml = "<TestRoot>%s</TestRoot>"

    def assertXMLEqual(self, first, second, msg=None):

        try:
            self.assertEqual(first, second, msg)
        except self.failureException:
            if len(first) != len(second):
                print("First len != second len")
            print(first)
            print(second)
            diffs = [None] * min(len(first), len(second))
            for i, (c1, c2) in enumerate(zip(first, second)):
                if c1 != c2:
                    diffs[i] = True

            for d in diffs:
                if d:
                    print("^", end="")
                else:
                    print(" ", end="")
            raise

    def test_agitation(self):
        expected_ag = """
<Cluster>
<Name>Agitation</Name>
<NumElts>3</NumElts>
<String>
<Name>pvUnit</Name>
<Val>RPM</Val>
</String>
<String>
<Name>manUnit</Name>
<Val>%</Val>
</String>
<String>
<Name>manName</Name>
<Val>Power</Val>
</String>
</Cluster>""".replace("\n", "")

        expected_ag = self.root_xml % expected_ag

        ag = hello_state.AgitationController()
        testroot = Element("TestRoot")
        actual_ag_ele = ag.mi_toxml(testroot)
        actual_ag = xml_tostring(actual_ag_ele).decode().replace("\n", "")
        self.assertXMLEqual(expected_ag, actual_ag)

    def test_temperature(self):

        expected_xml = """
<Cluster>
<Name>Temperature</Name>
<NumElts>3</NumElts>
<String>
<Name>pvUnit</Name>
<Val>°C</Val>
</String>
<String>
<Name>manUnit</Name>
<Val>%</Val>
</String>
<String>
<Name>manName</Name>
<Val>Heater Duty</Val>
</String>
</Cluster>""".replace("\n", "")

        expected_xml = self.root_xml % expected_xml

        temp = hello_state.TemperatureController()
        testroot = Element("TestRoot")
        actual_ele = temp.mi_toxml(testroot)
        actual_xml = xml_tostring(actual_ele, 'unicode').replace("\n", "")
        self.assertXMLEqual(expected_xml, actual_xml)

    def test_do(self):
        expected_xml = """<Cluster>
<Name>DO</Name>
<NumElts>5</NumElts>
<String>
<Name>pvUnit</Name>
<Val>%</Val>
</String>
<String>
<Name>manUpUnit</Name>
<Val>mL/min</Val>
</String>
<String>
<Name>manDownUnit</Name>
<Val>%</Val>
</String>
<String>
<Name>manUpName</Name>
<Val>O_2</Val>
</String>
<String>
<Name>manDownName</Name>
<Val>N_2</Val>
</String>
</Cluster>""".replace("\n", "")

        expected_xml = self.root_xml % expected_xml

        temp = hello_state.DOController()
        testroot = Element("TestRoot")
        actual_ele = temp.mi_toxml(testroot)
        actual_xml = xml_tostring(actual_ele, 'unicode').replace("\n", "")

        self.assertXMLEqual(expected_xml, actual_xml)

    def test_ph(self):
        expected_xml = """
<Cluster>
<Name>pH</Name>
<NumElts>5</NumElts>
<String>
<Name>pvUnit</Name>
<Val />
</String>
<String>
<Name>manUpUnit</Name>
<Val>%</Val>
</String>
<String>
<Name>manDownUnit</Name>
<Val>%</Val>
</String>
<String>
<Name>manUpName</Name>
<Val>Base</Val>
</String>
<String>
<Name>manDownName</Name>
<Val>CO_2</Val>
</String>
</Cluster>""".replace("\n", "")

        expected_xml = self.root_xml % expected_xml

        temp = hello_state.pHController()
        testroot = Element("TestRoot")
        actual_ele = temp.mi_toxml(testroot)
        actual_xml = xml_tostring(actual_ele, 'unicode').replace("\n", "")
        self.assertXMLEqual(expected_xml, actual_xml)

    def test_pressure(self):
        expected_xml = """<Cluster>
<Name>Pressure</Name>
<NumElts>1</NumElts>
<String>
<Name>pvUnit</Name>
<Val>psi</Val>
</String>
</Cluster>""".replace("\n", "")

        expected_xml = self.root_xml % expected_xml

        temp = hello_state.PressureController()
        testroot = Element("TestRoot")
        actual_ele = temp.mi_toxml(testroot)
        actual_xml = xml_tostring(actual_ele, 'unicode').replace("\n", "")

        self.assertXMLEqual(expected_xml, actual_xml)

    def test_level(self):
        expected_xml = """<Cluster>
<Name>Level</Name>
<NumElts>1</NumElts>
<String>
<Name>pvUnit</Name>
<Val>L</Val>
</String>
</Cluster>""".replace("\n", "")

        expected_xml = self.root_xml % expected_xml

        temp = hello_state.LevelController()
        testroot = Element("TestRoot")
        actual_ele = temp.mi_toxml(testroot)
        actual_xml = xml_tostring(actual_ele, 'unicode').replace("\n", "")

        self.assertXMLEqual(expected_xml, actual_xml)

    def test_condenser(self):
        expected_xml = """<Cluster>
<Name>Condenser</Name>
<NumElts>1</NumElts>
<String>
<Name>pvUnit</Name>
<Val>°C</Val>
</String>
</Cluster>""".replace("\n", "")

        expected_xml = self.root_xml % expected_xml

        temp = hello_state.FilterOvenController()
        testroot = Element("TestRoot")
        actual_ele = temp.mi_toxml(testroot)
        actual_xml = xml_tostring(actual_ele, 'unicode').replace("\n", '')

        self.assertXMLEqual(expected_xml, actual_xml)

from hello.mock.pid import delay_buffer


class TestMockPID(unittest.TestCase):
    def test_delay(self):

        d = delay_buffer(1, 1)
        self.assertEqual(d(1), 1)
        self.assertEqual(d(2), 1)
        self.assertEqual(d(3), 2)
        self.assertEqual(d(4), 3)

        d = delay_buffer(2, 1)

        self.assertEqual(d(2), 1)
        self.assertEqual(d(3), 1)
        self.assertEqual(d(4), 2)
        self.assertEqual(d(5), 3)
        self.assertEqual(d(6), 4)
        self.assertEqual(d(7), 5)

        d = delay_buffer(30, 1)

        for i in range(30):
            d(i)

        for i in range(30):
            self.assertEqual(d(i + 1), i)
        for i in range(30):
            self.assertEqual(d(i + 2), i + 1)
        for i in range(30):
            self.assertEqual(d(i + 3), i + 2)


from hello.mock.util import HelloXMLGenerator, xml_tostring
from xml.etree.ElementTree import Element, XML
from itertools import zip_longest


class TestXMLUtilities(unittest.TestCase):
    """ Test functions related to generating XML/json from
    arbitrary python object trees.
    """

    def assertElementEqual(self, first, second, msg=None):
        if msg is None:
            msg = ''
        self.assertIsInstance(first, Element, msg + "First argument is not an Element")
        self.assertIsInstance(second, Element, msg + "First argument is not an Element")

        # compare basic attributes

        name1 = str(first)
        name2 = str(second)
        self.assertEqual(first.tag, second.tag, msg + "Element tags do not match (%s != %s)" % (name1, name2))
        self.assertEqual(first.text, second.text, msg + "Element text does not match(%s != %s)" % (name1, name2))
        self.assertEqual(first.attrib, second.attrib, msg + "Element attributes do not match(%s != %s)"
                         % (name1, name2))
        self.assertEqual(first.tail, second.tail, msg + "Element tails do not match(%s != %s)" % (name1, name2))

        for f, s in zip_longest(first, second):
            self.assertElementEqual(f, s, msg)

    def setUp(self):
        self.addTypeEqualityFunc(Element, self.assertElementEqual)
        self.generator = HelloXMLGenerator()

    def test_obj_to_xml(self):
        obj_to_xml = self.generator.obj_to_xml

        obj = [
            ('test1', 'Foo'),
            ('test2', 'Bar'),
            ('test3', 'Baz')
        ]
        actual_txt = obj_to_xml(obj)

        expected = b"""<?xml version="1.0" encoding="windows-1252" standalone="no" ?><Reply><Result>True</Result><Message>
<NumElts>3</NumElts>
<String>
<Name>test1</Name>
<Val>Foo</Val>
</String>
<String>
<Name>test2</Name>
<Val>Bar</Val>
</String>
<String>
<Name>test3</Name>
<Val>Baz</Val>
</String>
</Message></Reply>"""

        exp_no_newline = expected.replace(b"\n", b"")
        actual_no_newline = actual_txt.replace(b"\n", b"")

        # print(exp_no_newline)
        # print(actual_no_newline)

        self.assertEqual(exp_no_newline, actual_no_newline)
        try:
            self.assertEqual(expected, actual_txt)
        except:
            for l1, l2 in zip(expected.splitlines(), actual_txt.splitlines()):
                self.assertEqual(l1, l2)
            raise


    def test_xmlgenerator_strotoxml(self):
        """
        Basic test that all the individual parsing functions work.
        """
        strtoxml = self.generator.str_toxml

        actual_root = Element("TestRoot")
        actual_root.text = "\n"
        strtoxml("Foo", "test1", actual_root)
        strtoxml("Bar", "test2", actual_root)
        strtoxml("Baz", "test3", actual_root)

        expected = XML("""<TestRoot>
<String>
<Name>test1</Name>
<Val>Foo</Val>
</String>
<String>
<Name>test2</Name>
<Val>Bar</Val>
</String>
<String>
<Name>test3</Name>
<Val>Baz</Val>
</String>
</TestRoot>"""
        )

        self.assertEqual(expected, actual_root)

    def test_xmlgenerator_intoxml(self):
        """
        Basic test that all the individual parsing functions work.
        """
        testfunc = self.generator.int_toxml

        actual_root = Element("TestRoot")
        actual_root.text = "\n"
        testfunc(1, "test1", actual_root)
        testfunc(2, "test2", actual_root)
        testfunc(3, "test3", actual_root)

        expected = XML(
"""<TestRoot>
<U32>
<Name>test1</Name>
<Val>1</Val>
</U32>
<U32>
<Name>test2</Name>
<Val>2</Val>
</U32>
<U32>
<Name>test3</Name>
<Val>3</Val>
</U32>
</TestRoot>"""
)

        self.assertEqual(expected, actual_root)

    def test_xmlgenerator_floattoxml(self):
        """
        Basic test that all the individual parsing functions work.
        """
        testfunc = self.generator.float_toxml

        actual_root = Element("TestRoot")
        actual_root.text = "\n"
        testfunc(1.0, "test1", actual_root)
        testfunc(2.0, "test2", actual_root)
        testfunc(3.0, "test3", actual_root)

        expected = XML(
"""<TestRoot>
<SGL>
<Name>test1</Name>
<Val>1.0</Val>
</SGL>
<SGL>
<Name>test2</Name>
<Val>2.0</Val>
</SGL>
<SGL>
<Name>test3</Name>
<Val>3.0</Val>
</SGL>
</TestRoot>"""
)

        self.assertEqual(expected, actual_root)
        
    def test_xmlgenerator_listtoxml(self):
        testfunc = self.generator.list_toxml
        
        actual_root = Element("TestRoot")
        actual_root.text = "\n"
        l1 = [
            ('list1.1', 1),
            ('list1.2', 2),
            ('list1.3', 3)
        ]
        l2 = [
            ('list2.1', 1.5),
            ('list2.2', 2.5),
            ('list2.3', 3.5),
            ('list2.4', 4.5)
        ]
        l3 = [
            ('list3.1', 'one'),
            ('list3.2', 'two'),
            ('list3.3', 'three'),
            ('list3.4', 'four'),
            ('list3.5', 'five')
        ]
        testfunc(l1, "test1", actual_root)
        testfunc(l2, "test2", actual_root)
        testfunc(l3, "test3", actual_root)

        sub_tmplt = "<%s>\n<Name>%s</Name>\n<Val>%s</Val>\n</%s>"

        sub1 = '\n'.join(sub_tmplt % ("U32", k, v, "U32") for k, v in l1)
        sub2 = '\n'.join(sub_tmplt % ("SGL", k, v, "SGL") for k, v in l2)
        sub3 = '\n'.join(sub_tmplt % ("String", k, v, "String") for k, v in l3)

        xml = """<TestRoot>
<Cluster>
<Name>test1</Name>
<NumElts>3</NumElts>
%s
</Cluster>
<Cluster>
<Name>test2</Name>
<NumElts>4</NumElts>
%s
</Cluster>
<Cluster>
<Name>test3</Name>
<NumElts>5</NumElts>
%s
</Cluster>
</TestRoot>""" % (sub1, sub2, sub3)
        expected = XML(xml)

        self.assertEqual(expected, actual_root)

    def test_xmlgenerator_tupletoxml(self):
        # same test function as above, but with tuples
        testfunc = self.generator.list_toxml

        actual_root = Element("TestRoot")
        actual_root.text = "\n"
        l1 = (
            ('list1.1', 1),
            ('list1.2', 2),
            ('list1.3', 3)
        )
        l2 = (
            ('list2.1', 1.5),
            ('list2.2', 2.5),
            ('list2.3', 3.5),
            ('list2.4', 4.5)
        )
        l3 = (
            ('list3.1', 'one'),
            ('list3.2', 'two'),
            ('list3.3', 'three'),
            ('list3.4', 'four'),
            ('list3.5', 'five')
        )
        testfunc(l1, "test1", actual_root)
        testfunc(l2, "test2", actual_root)
        testfunc(l3, "test3", actual_root)

        sub_tmplt = "<%s>\n<Name>%s</Name>\n<Val>%s</Val>\n</%s>"

        sub1 = '\n'.join(sub_tmplt % ("U32", k, v, "U32") for k, v in l1)
        sub2 = '\n'.join(sub_tmplt % ("SGL", k, v, "SGL") for k, v in l2)
        sub3 = '\n'.join(sub_tmplt % ("String", k, v, "String") for k, v in l3)

        xml = """<TestRoot>
<Cluster>
<Name>test1</Name>
<NumElts>3</NumElts>
%s
</Cluster>
<Cluster>
<Name>test2</Name>
<NumElts>4</NumElts>
%s
</Cluster>
<Cluster>
<Name>test3</Name>
<NumElts>5</NumElts>
%s
</Cluster>
</TestRoot>""" % (sub1, sub2, sub3)
        expected = XML(xml)

        self.assertEqual(expected, actual_root)

    def test_xmlgenerator_dicttoxml(self):
        testfunc = self.generator.dict_toxml

        actual_root = Element("TestRoot")
        l1 = dict([
            ('list1.1', 1),
            ('list1.2', 2),
            ('list1.3', 3)
        ])
        l2 = dict([
            ('list2.1', 1.5),
            ('list2.2', 2.5),
            ('list2.3', 3.5),
            ('list2.4', 4.5)
        ])
        l3 = dict([
            ('list3.1', 'one'),
            ('list3.2', 'two'),
            ('list3.3', 'three'),
            ('list3.4', 'four'),
            ('list3.5', 'five')
        ])
        testfunc(l1, "test1", actual_root)
        testfunc(l2, "test2", actual_root)
        testfunc(l3, "test3", actual_root)

        sub_tmplt = "<%s>\n<Name>%s</Name>\n<Val>%s</Val>\n</%s>"

        sub1 = '\n'.join(sub_tmplt % ("U32", k, v, "U32") for k, v in l1.items())
        sub2 = '\n'.join(sub_tmplt % ("SGL", k, v, "SGL") for k, v in l2.items())
        sub3 = '\n'.join(sub_tmplt % ("String", k, v, "String") for k, v in l3.items())

        xml = """<TestRoot>
<Cluster>
<Name>test1</Name>
<NumElts>3</NumElts>
%s
</Cluster>
<Cluster>
<Name>test2</Name>
<NumElts>4</NumElts>
%s
</Cluster>
<Cluster>
<Name>test3</Name>
<NumElts>5</NumElts>
%s
</Cluster>
</TestRoot>""" % (sub1, sub2, sub3)
        expected = XML(xml)

        # this is ugly, but the easiest way of checking whether
        # the resulting everything is ordered or not.
        # of course, it relies on HelloXML working properly.
        # init is overridden to prevent the auto parsing.
        from hello.hello import HelloXML
        class DebugXML(HelloXML):
            def __init__(self):
                pass

        exp_dict = DebugXML().parse(expected)[1]
        actual_dict = DebugXML().parse(actual_root)[1]
        self.assertEqual(actual_dict, exp_dict)

        # self.assertUnorderedXMLEqual(expected, actual_root)

    def test_xmlgenerator_odtoxml(self):
        from collections import OrderedDict
        testfunc = self.generator.dict_toxml

        actual_root = Element("TestRoot")
        actual_root.text = "\n"
        l1 = OrderedDict([
            ('list1.1', 1),
            ('list1.2', 2),
            ('list1.3', 3)
        ])
        l2 = OrderedDict([
            ('list2.1', 1.5),
            ('list2.2', 2.5),
            ('list2.3', 3.5),
            ('list2.4', 4.5)
        ])
        l3 = OrderedDict([
            ('list3.1', 'one'),
            ('list3.2', 'two'),
            ('list3.3', 'three'),
            ('list3.4', 'four'),
            ('list3.5', 'five')
        ])
        testfunc(l1, "test1", actual_root)
        testfunc(l2, "test2", actual_root)
        testfunc(l3, "test3", actual_root)

        sub_tmplt = "<%s>\n<Name>%s</Name>\n<Val>%s</Val>\n</%s>"

        sub1 = '\n'.join(sub_tmplt % ("U32", k, v, "U32") for k, v in l1.items())
        sub2 = '\n'.join(sub_tmplt % ("SGL", k, v, "SGL") for k, v in l2.items())
        sub3 = '\n'.join(sub_tmplt % ("String", k, v, "String") for k, v in l3.items())

        xml = """<TestRoot>
<Cluster>
<Name>test1</Name>
<NumElts>3</NumElts>
%s
</Cluster>
<Cluster>
<Name>test2</Name>
<NumElts>4</NumElts>
%s
</Cluster>
<Cluster>
<Name>test3</Name>
<NumElts>5</NumElts>
%s
</Cluster>
</TestRoot>""" % (sub1, sub2, sub3)

        expected = XML(xml)

        # because ordered dict should be ordered,
        # use the standard ordered comparison function
        self.assertEqual(expected, actual_root)

    def test_xmlgenerator_itertoxml(self):
        # same test function as above, but with tuples
        testfunc = self.generator.list_toxml

        actual_root = Element("TestRoot")
        actual_root.text = "\n"
        l1 = (
            ('list1.1', 1),
            ('list1.2', 2),
            ('list1.3', 3)
        )
        l2 = (
            ('list2.1', 1.5),
            ('list2.2', 2.5),
            ('list2.3', 3.5),
            ('list2.4', 4.5)
        )
        l3 = (
            ('list3.1', 'one'),
            ('list3.2', 'two'),
            ('list3.3', 'three'),
            ('list3.4', 'four'),
            ('list3.5', 'five')
        )

        def iterator(lst):
            for item in lst:
                yield item

        i1 = iterator(l1)
        i2 = iterator(l2)
        i3 = iterator(l3)

        testfunc(l1, "test1", actual_root)
        testfunc(l2, "test2", actual_root)
        testfunc(l3, "test3", actual_root)

        sub_tmplt = "<%s>\n<Name>%s</Name>\n<Val>%s</Val>\n</%s>"

        sub1 = '\n'.join(sub_tmplt % ("U32", k, v, "U32") for k, v in i1)
        sub2 = '\n'.join(sub_tmplt % ("SGL", k, v, "SGL") for k, v in i2)
        sub3 = '\n'.join(sub_tmplt % ("String", k, v, "String") for k, v in i3)

        xml = """<TestRoot>
<Cluster>
<Name>test1</Name>
<NumElts>3</NumElts>
%s
</Cluster>
<Cluster>
<Name>test2</Name>
<NumElts>4</NumElts>
%s
</Cluster>
<Cluster>
<Name>test3</Name>
<NumElts>5</NumElts>
%s
</Cluster>
</TestRoot>""" % (sub1, sub2, sub3)
        expected = XML(xml)

        self.assertEqual(expected, actual_root)


if __name__ == '__main__':
    unittest.main()
