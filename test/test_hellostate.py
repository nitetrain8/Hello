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


class MyTestCase(unittest.TestCase):
    def test_something(self):
        """
        @return: None
        @rtype: None
        """
        self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()
