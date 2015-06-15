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


from hello.hello import HelloApp, HelloXML, BatchListXML, BatchEntry
import pickle


global_ipv4 = "localhost:12345"


class DummyRsp():
    """
    HelloXML only supports string objects & those with
    "read" methods.
    """

    def __init__(self, txt):
        self.txt = txt

    def read(self, n):
        if not self.txt:
            return b''
        if n > len(self.txt):
            rv = self.txt
            self.txt = b""
        else:
            rv = self.txt[:n]
            self.txt = self.txt[n:]
        return rv


class TestPickle(unittest.TestCase):

    def setUp(self):
        self.app = HelloApp(global_ipv4)

    def tearDown(self):
        self.app.close()

    def test_pickle1(self):
        """
        @return: None
        @rtype: None
        """

        try:
            pickle.dumps(self.app)
        except pickle.PickleError as e:
            self.fail(str(e))


class TestHelloXML(unittest.TestCase):

    def setUp(self):
        self.app = HelloApp(global_ipv4)

    def tearDown(self):
        self.app.close()

    def test_getconfig(self):

        fp = join(test_input, "good_getconfig.pkl")

        with open(fp, 'rb') as f:
            raw, exp_dict = pickle.load(f)

        res_dict = HelloXML(DummyRsp(raw)).data

        self.assertEqual(exp_dict, res_dict)

    def _generate_test_getconfig_data_(self):

        fp = join(test_input, "good_getconfig.pkl")
        raw = self.app.send_request("?&call=getConfig").read()

        data = HelloXML(DummyRsp(raw)).data

        with open(fp, 'wb') as f:
            pickle.dump((raw, data), f)


class TestBatchXML(unittest.TestCase):
    def setUp(self):
        self.app = HelloApp('192.168.1.82')
        self.addTypeEqualityFunc(BatchEntry, self.assertBatchEntryEqual)

    def tearDown(self):
        self.app.close()

    def assertBatchEntryEqual(self, exp, res, msg=""):
        keys = (
                "id", "name", "product_number",
                "rev", "serial_number", "start_time",
                "stop_time", "user"
            )
        for key in keys:
            self.assertEqual(exp[key], res[key], msg)

    def test_basic(self):
        fp = join(test_input, "good_getbatches.pkl")

        with open(fp, 'rb') as f:
            raw, exp_dict = pickle.load(f)

        res_dict = BatchListXML(DummyRsp(raw)).data

        self.assertEqual(list(exp_dict.keys()), list(res_dict.keys()))
        for key in exp_dict:
            self.assertEqual(exp_dict[key], res_dict[key])

    def _generate_test_getconfig_data_(self):
        fp = join(test_input, "good_getbatches.pkl")
        raw = self.app.send_request("?&call=getBatches").read()

        data = BatchListXML(DummyRsp(raw)).data

        with open(fp, 'wb') as f:
            pickle.dump((raw, data), f)



if __name__ == '__main__':
    unittest.main()
