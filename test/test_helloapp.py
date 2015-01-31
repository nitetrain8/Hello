"""

Created by: Nathan Starkweather
Created on: 01/30/2015
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


from hello.hello import HelloApp


class TestPickle(unittest.TestCase):

    def setUp(self):
        self.app = HelloApp('192.168.1.4')

    def tearDown(self):
        self.app.close()

    def test_pickle1(self):
        """
        @return: None
        @rtype: None
        """
        import pickle
        try:
            pickle.dumps(self.app)
        except pickle.PickleError as e:
            self.fail(str(e))


if __name__ == '__main__':
    unittest.main()
