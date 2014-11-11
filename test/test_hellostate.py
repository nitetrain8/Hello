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


from hello.mock.state import SimpleController, TwoWayController, SmallController, HelloState
from json import loads as json_loads, dumps as json_dumps

class TestStateJson(unittest.TestCase):
    def test_SimpleController(self):
        """
        @return: None
        @rtype: None
        """
        c = SimpleController("TestSimpleController")
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

        actual = c.todict()

        self.assertEqual(expected, actual)

    def test_TwoWayController(self):
        c = TwoWayController("TestTwoWayController")
        c.pv = 1
        c.sp = 2
        c.manup = 3
        c.mandown = 4
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

        actual = c.todict()

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

        actual = c.todict()

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
        s.do.mandown = 9
        s.do.manup = 10
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
        s.ph.mandown = 30
        s.ph.manup = 31
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
                'agitation': {
                    'error': 1,
                    'interlocked': 2,
                    'man': 3,
                    'mode': 4,
                    'pv': 5,
                    'sp': 6,
                },

                'do': {
                    'error': 7,
                    'interlocked': 8,
                    'manDown': 9,
                    'manUp': 10,
                    'mode': 11,
                    'pv': 12,
                    'sp': 13,
                },

                'condensor': {
                    'error': 14,
                    'mode': 15,
                    'pv': 16,

                },

                'level': {
                    'error': 18,
                    'mode': 19,
                    'pv': 20,

                },

                'maingas': {
                    'error': 22,
                    'interlocked': 23,
                    'man': 24,
                    'mode': 25,
                    'pv': 26,
                    'sp': 27,
                },

                'ph': {
                    'error': 28,
                    'interlocked': 29,
                    'manDown': 30,
                    'manUp': 31,
                    'mode': 32,
                    'pv': 33,
                    'sp': 34,
                },

                'pressure': {
                    'error': 35,
                    'mode': 36,
                    'pv': 37,
                },

                'secondaryheat': {
                    'error': 39,
                    'interlocked': 40,
                    'man': 41,
                    'mode': 42,
                    'pv': 43,
                    'sp': 44,
                },

                'temperature': {
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
        except:
            # the standard dict assert equal message sucks,
            # so if the test fails, loop manually here to get a
            # better error message
            self.assertEqual(expected.keys(), actual.keys())
            emsg = expected['message']
            amsg = actual['message']
            self.assertEqual(emsg.keys(), amsg.keys())
            for ekey in emsg:
                self.assertIn(ekey, amsg)
                eval = emsg[ekey]
                aval = amsg[ekey]
                for ekey2 in eval:
                    self.assertIn(ekey2, aval)
                    eval2 = eval[ekey2]
                    aval2 = aval[ekey2]
                    self.assertEqual(eval2, aval2)
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

if __name__ == '__main__':
    unittest.main()
