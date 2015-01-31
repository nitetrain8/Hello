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

test_dir = dirname(__file__)
temp_dir = join(test_dir, "temp")
test_input = join(test_dir, "test_input")

getconfig_file = test_input + "/" + "GetConfig.xml"
getconfig_xml = None


def setUpModule():
    for d in (temp_dir, test_input):
        try:
            makedirs(d)
        except FileExistsError:
            pass

    def make_xml():
        from urllib.request import urlopen

        url = "http://71.189.82.196:6/webservice/interface/?&call=getConfig"
        rsp = urlopen(url)
        xml = rsp.read()

        # Cache result for future use.
        with open(getconfig_file, 'wb') as f:
            f.write(xml)

        return xml

    from os.path import exists
    global getconfig_xml
    if exists(getconfig_file):
        with open(getconfig_file, 'rb') as f:
            getconfig_xml = f.read()
    else:
        getconfig_xml = make_xml()


def tearDownModule():
    try:
        rmtree(temp_dir)
    except FileNotFoundError:
        pass


from hello.hello import HelloXML


class TestXMLParse(unittest.TestCase):
    def test_xml_parse_basic(self):
        """
        @return: None
        @rtype: None
        """
        xml = "<myxml><Result>True</Result><Message><foo>bar!</foo></Message></myxml>"
        rsp = HelloXML(xml).getdata()
        exp = {"foo": "bar!"}
        self.assertEqual(exp, rsp)

    @unittest.skip
    def test_xml_parse_getconfig(self):
        from hello.hello import HelloApp

        app = HelloApp('192.168.1.12')
        rsp = app.getConfig()
        xml = rsp.read()

        print(HelloXML(xml))
        print(xml)

    def test_getconfig(self):

        with open(getconfig_file, 'rb') as f:
            xml = f.read()

        p = HelloXML(xml).getdata()
        self.fail()


if __name__ == '__main__':
    unittest.main()
