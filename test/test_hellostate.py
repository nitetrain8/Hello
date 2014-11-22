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
from json import loads as json_loads, dumps as json_dumps

class TestStateJson(unittest.TestCase):
    def test_SimpleController(self):
        """
        @return: None
        @rtype: None
        """
        c = StandardController("TestSimpleController")
        c.pv = 1
        c.sp = 2
        c.man = 3
        c.mode = 4
        c.error = 5
        c.interlocked = 6

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

    def test_TwoWayController(self):
        c = TwoWayController("TestTwoWayController")
        c.pv = 1
        c.sp = 2
        c.manUp = 3
        c.manDown = 4
        c.mode = 5
        c.error = 6
        c.interlocked = 7

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

    def test_SmallController(self):
        c = SmallController("TestSmallController")
        c.pv = 1
        c.sp = 2
        c.mode = 3
        c.error = 4

        expected = {
            'pv': 1,
            'mode': 3,
            'error': 4
        }

        actual = c.mv_todict()

        self.assertEqual(expected, actual)

    def test_HelloState(self):
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

                'Condensor': {
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

        # these won't match, because dict order is arbitrary
        expected_json = json_dumps(expected)
        actual_json = json_dumps(actual)

        # loading the dump dict back should match, though
        expected_from_json = json_loads(expected_json)
        actual_from_json = json_loads(actual_json)

        self.assertEqual(expected_from_json, actual_from_json)


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
        self.assertEqual(first.tag, second.tag, msg + "Element tags do not match")
        self.assertEqual(first.text, second.text, msg + "Element text does not match")
        self.assertEqual(first.attrib, second.attrib, msg + "Element attributes do not match")
        self.assertEqual(first.tail, second.tail, msg + "Element tails do not match")

        for f, s in zip_longest(first, second):
            self.assertEqual(f, s, msg)

    def setUp(self):
        self.addTypeEqualityFunc(Element, self.assertElementEqual)
        self.generator = HelloXMLGenerator()

    def test_xmlgenerator_strotoxml(self):
        """
        Basic test that all the individual parsing functions work.
        """
        strtoxml = self.generator.str_toxml

        actual_root = Element("TestRoot")
        strtoxml("Foo", "test1", actual_root)
        strtoxml("Bar", "test2", actual_root)
        strtoxml("Baz", "test3", actual_root)

        expected = XML(
        """<TestRoot>
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
        </TestRoot>""".replace(" ", "").replace("\n", "")
        )

        self.assertEqual(expected, actual_root)

    def test_xmlgenerator_intoxml(self):
        """
        Basic test that all the individual parsing functions work.
        """
        testfunc = self.generator.int_toxml

        actual_root = Element("TestRoot")
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
            </TestRoot>""".replace(" ", "").replace("\n", "")
        )

        self.assertEqual(expected, actual_root)

    def test_xmlgenerator_floattoxml(self):
        """
        Basic test that all the individual parsing functions work.
        """
        testfunc = self.generator.float_toxml

        actual_root = Element("TestRoot")
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
            </TestRoot>""".replace(" ", "").replace("\n", "")
        )

        self.assertEqual(expected, actual_root)
        
    def test_xmlgenerator_listtoxml(self):
        testfunc = self.generator.list_toxml
        
        actual_root = Element("TestRoot")
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

        sub_tmplt = "<%s><Name>%s</Name><Val>%s</Val></%s>"

        sub1 = ''.join(sub_tmplt % ("U32", k, v, "U32") for k, v in l1)
        sub2 = ''.join(sub_tmplt % ("SGL", k, v, "SGL") for k, v in l2)
        sub3 = ''.join(sub_tmplt % ("String", k, v, "String") for k, v in l3)

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
        xml = xml.replace(" ", "").replace("\n", "")
        expected = XML(xml)

        self.assertEqual(expected, actual_root)

    def test_xmlgenerator_tupletoxml(self):
        # same test function as above, but with tuples
        testfunc = self.generator.list_toxml

        actual_root = Element("TestRoot")
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

        sub_tmplt = "<%s><Name>%s</Name><Val>%s</Val></%s>"

        sub1 = ''.join(sub_tmplt % ("U32", k, v, "U32") for k, v in l1)
        sub2 = ''.join(sub_tmplt % ("SGL", k, v, "SGL") for k, v in l2)
        sub3 = ''.join(sub_tmplt % ("String", k, v, "String") for k, v in l3)

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
        xml = xml.replace(" ", "").replace("\n", "")
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

        sub_tmplt = "<%s><Name>%s</Name><Val>%s</Val></%s>"

        sub1 = ''.join(sub_tmplt % ("U32", k, v, "U32") for k, v in l1.items())
        sub2 = ''.join(sub_tmplt % ("SGL", k, v, "SGL") for k, v in l2.items())
        sub3 = ''.join(sub_tmplt % ("String", k, v, "String") for k, v in l3.items())

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
        xml = xml.replace(" ", "").replace("\n", "")
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

        sub_tmplt = "<%s><Name>%s</Name><Val>%s</Val></%s>"

        sub1 = ''.join(sub_tmplt % ("U32", k, v, "U32") for k, v in l1.items())
        sub2 = ''.join(sub_tmplt % ("SGL", k, v, "SGL") for k, v in l2.items())
        sub3 = ''.join(sub_tmplt % ("String", k, v, "String") for k, v in l3.items())

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
        xml = xml.replace(" ", "").replace("\n", "")
        expected = XML(xml)

        # because ordered dict should be ordered,
        # use the standard ordered comparison function
        self.assertEqual(expected, actual_root)

    def test_xmlgenerator_itertoxml(self):
        # same test function as above, but with tuples
        testfunc = self.generator.list_toxml

        actual_root = Element("TestRoot")
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

        sub_tmplt = "<%s><Name>%s</Name><Val>%s</Val></%s>"

        sub1 = ''.join(sub_tmplt % ("U32", k, v, "U32") for k, v in i1)
        sub2 = ''.join(sub_tmplt % ("SGL", k, v, "SGL") for k, v in i2)
        sub3 = ''.join(sub_tmplt % ("String", k, v, "String") for k, v in i3)

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
        xml = xml.replace(" ", "").replace("\n", "")
        expected = XML(xml)

        self.assertEqual(expected, actual_root)


if __name__ == '__main__':
    unittest.main()
