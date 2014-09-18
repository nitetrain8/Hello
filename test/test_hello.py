"""

Created by: Nathan Starkweather
Created on: 09/17/2014
Created in: PyCharm Community Edition

Module: test_module
Functions: test_functions

"""
import unittest
from os import makedirs
from os.path import dirname, join, exists
from shutil import rmtree

__author__ = 'PBS Biotech'

curdir = dirname(__file__)
test_dir = dirname(curdir)
test_temp_dir = join(test_dir, "temp")
temp_dir = join(test_temp_dir, "temp_dir_path")
test_input = join(curdir, "test_input")


def setUpModule():
    try:
        makedirs(temp_dir)
    except FileExistsError:
        pass


def tearDownModule():
    try:
        rmtree(temp_dir)
    except FileNotFoundError:
        pass


from hello.hello import parse_XML


class TestXMLParse(unittest.TestCase):
    def test_xml_parse_basic(self):
        """
        @return: None
        @rtype: None
        """
        xml = "<myxml><foo>bar!</foo></myxml>"
        rsp = parse_XML(xml)
        exp = {"foo": "bar!"}
        self.assertEqual(exp, rsp)

    def test_xml_parse_getconfig(self):
        from hello.hello import HelloApp

        app = HelloApp('192.168.1.6')
        rsp = app.getconfig()
        xml = rsp.read()

        print(parse_XML(xml))
        print(xml)


if __name__ == '__main__':
    unittest.main()
