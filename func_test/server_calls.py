"""

Created by: Nathan Starkweather
Created on: 11/05/2014
Created in: PyCharm Community Edition


"""
from unittest.case import SkipTest

__author__ = 'Nathan Starkweather'

from hello import HelloApp, HelloXML, BatchListXML, parse_xml, parse_rsp
import unittest
from os.path import dirname
from json import loads as json_loads

here = dirname(__file__)
with open('\\'.join((here, 'ipaddys.txt')), 'r') as f:
    ipaddys = f.read().splitlines()

if not ipaddys:
    ipaddys = ['192.168.1.6']


class DebugXML(HelloXML):
    """ copy of helloxml, but doesn't raise
    TrueError. This is used since the test fixture
    uses the xml-to-dict parser to parse both set
    and get responses.
    """
    # noinspection PyMissingConstructor
    def __init__(self, xml):

        if isinstance(xml, str):
            root = parse_xml(xml)
        else:
            root = parse_rsp(xml)

        self._parse_types = self._parse_types
        self._parsed = False

        # begin
        name, parsed = self.parse(root)
        self.parse_dict = {name: parsed}
        self.reply = parsed
        self.result = parsed['Result'] == 'True'
        self.data = self.msg = parsed['Message']
        self.truemsg = self.msg == 'True'

        self._parsed = True


class TestServerCalls(unittest.TestCase):

    _all_server_calls = {
        "login",
        "getVersion",
        "getMainInfo",
        "getTrendData",
        "getAlarmList",
        "getUsers",
        "getMainValues",
        "getUnAckCount",
        "getLoginStatus",
        "getUserInfo",
        "getDORAValues",
        "getAction",
        "setTopLight",
        "setUnlockDoor",
        "getAdvancedValues",
        "getConfig",
        "setconfig",
        "getAlarms",
        "clearAlarm",
        "clearAlarmsByType",
        "clearAllAlarms",
        "revertTrialCal",
        "getRawValue",
        "tryCal",
        "runRecipe",
        "getRecipeItems",
        "getRecipeStep",
        "recipeSkip",
        "getBatches",
        "getReportTypes",
        "getReport",
        "getPumps",
        "setpumpa",
        "setpumpb",
        "setpumpc",
        "setpumpsample",
        "getPumps",
        "loadbag",
        "getBagConfig",
        "setStartBatch",
        "setendbatch",
        "getSensorStates",
        "setSensorState",
        "set",
        "getRecipes",
        "shutdown",
        "logout"
    }
    ipaddy = '192.168.1.6:80'
    logged_in = False
    calls_seen = None

    @classmethod
    def setUpClass(cls):
        cls.app = None
        cls.logged_in = False
        cls.calls_seen = set()

    @classmethod
    def tearDownClass(cls):
        diff = cls._all_server_calls - cls.calls_seen
        if diff:
            print()
            print("Warning, calls untested:")
            for d in diff:
                print(d)

    def setUp(self):
        if self.app is None:
            self.app = HelloApp(self.ipaddy)
            self.logged_in = False

    def tearDown(self):
        if self.app:
            self.app.close()
            self.app = None

    def _validate_xml_get(self, call, rsp):
        if call == 'getBatches':
            parser = BatchListXML
        else:
            parser = HelloXML

        xml = parser(rsp)
        result = xml.result
        msg = xml.data
        if not result:
            raise self.failureException(msg)
        self.assertNotEqual(msg, 'True')

    def _validate_json_get(self, rsp):
        txt = rsp.read().decode("utf-8")
        json = json_loads(txt)
        try:
            result = json['Result'] == 'True'
        except KeyError:
            try:
                result = json['result'] == 'True'
            except KeyError:
                result = False

        msg = json['message']

        if not result:
            raise self.failureException(msg)
        self.assertNotEqual(msg, 'True')

    def _validate_set(self, rsp):

        xml = DebugXML(rsp)
        result = xml.result
        msg = xml.msg
        if not result:
            raise self.failureException(msg)
        self.assertTrue(msg, 'True')

    def login(self, force=False):

        if not self.logged_in or force:
            self.app.login()
            self.logged_in = True

    def logout(self, force=False):
        if self.logged_in or force:
            self.app.logout()
            self.logged_in = False

    def do_get_call(self, call, args=(), rtype='xml', needlogin=False):
        if not self.logged_in and needlogin:
            self.login(True)
        rsp = self.app.call_hello_from_args2(call, args)
        self.calls_seen.add(call)
        if rtype == 'json':
            self._validate_json_get(rsp)
        else:
            self._validate_xml_get(call, rsp)

    def do_set_call(self, call, args=(), needlogin=True):
        if not self.logged_in and needlogin:
            self.login(True)
        rsp = self.app.call_hello_from_args2(call, args)
        self.calls_seen.add(call)
        self._validate_set(rsp)

    def test_getVersion(self):
        """
        @return: None
        @rtype: None
        """
        self.do_get_call('getVersion')

    def test_getMainInfo(self):
        self.do_get_call('getMainInfo')

    # @unittest.skip("Takes a long time")
    def test_getTrendData(self):

        # for brevity, generate all combos of parameters dynamically.
        # The weird listcomp format is so that data is easily accessible
        # in the test loop at the expense of readability here. The
        # format is (span, group, (args))
        spans = "15min", "2hr", "12hr", "24hr", "72hr", "7day"
        groups = "agitation", "ph", "do", "temperature"
        combos = [(
                      s,
                      g, (
                          ('span', s),
                          ('group', g),
                          ('json', '1')
                      )
                  ) for s in spans for g in groups]

        for span, group, args in combos:
            self.do_get_call('getTrendData', args, 'json')

    def test_getAlarmList(self):
        self.do_get_call('getAlarmList')

    def test_getUsers(self):
        self.do_get_call('getUsers')

    # prefix login and logout methods so that they are sorted
    # to be the first and last tests run, respectively.

    def test_AA_login(self):

        args = (
            ('val1', 'user1'),
            ('val2', '12345'),
            ("loader", "Authenticating..."),
            ("skipValidate", "true")
        )
        self.do_set_call('login', args, False)
        self.logged_in = True

    def test_zz_logout(self):
        self.do_set_call('logout')

    def test_getMainValues(self):
        self.do_get_call('getMainValues', (('json', 'True'),), 'json')

    def test_getUnAckCount(self):
        self.do_get_call('getUnAckCount')

    def test_getLoginStatus(self):
        self.do_get_call("getLoginStatus", (("Loader", 'Verifying...'),))

    def test_getUserInfo(self):
        self.login()
        self.do_get_call("getUserInfo", (), 'xml', True)

    def test_getDORAValues(self):
        self.do_get_call("getDORAValues")

    def test_getAction(self):
        self.do_get_call("getAction")

    def test_setTopLight(self):
        self.do_set_call("setTopLight")

    @unittest.skip("Really Loud")
    def test_setUnlockDoor(self):
        # this will cause a failure if the door is
        # interlocked but call works todo- find a way around this

        # inline do_set_call
        if not self.logged_in:
            self.login(True)
        rsp = self.app.call_hello_from_args2('setUnlockDoor')
        self.calls_seen.add('setUnlockDoor')

        # inline validate_set
        xml = HelloXML(rsp)
        result = xml.result
        msg = xml.msg
        if not result:
            if "Interlock" in msg and msg.endswith("7402"):
                pass
            else:
                raise self.failureException(msg)
        else:
            self.assertEqual(msg, 'True')

    def test_getAdvancedValues(self):
        self.do_get_call("getAdvancedValues")

    def test_getConfig(self):
        self.do_get_call("getConfig")

    def test_setConfig(self):
        args = (
            ('group', 'temperature'),
            ('name', 'P_Gain_(%25%2FC)'),
            ('val', '40.000')
        )
        self.do_set_call('setConfig', args)

    def test_getAlarms(self):
        # I don't have any idea what these do
        args = (
            ('mode', 'first'),
            ('val1', '100'),
            ('val2', '1'),
            ('loader', 'Loading+alarms...')
        )
        self.do_get_call('getAlarms', args)

    def test_clearAlarm(self):
        alarms = self.app.getAlarms()
        ids = alarms['alarmIDs'].split(',')
        try:
            alarm = ids[0]
        except IndexError:
            raise SkipTest("No alarms, can't test")

        self.login()
        self.do_set_call('clearAlarm', (('val1', alarm),))

    def test_clearAlarmsByType(self):

        alarms = self.app.getAlarms()
        types = alarms['type'].split(',')
        try:
            typ = types[1]
        except IndexError:
            raise SkipTest("No alarms, can't test")

        self.login()
        self.do_set_call("clearAlarmsByType", (('val1', typ),))

    def test_revertTrialCal(self):
        self.login()
        sensors = "pha", "phb", "doa", "dob", "level", "pressure"
        for s in sensors:
            self.do_set_call('revertTrialCal', (('sensor', s),))

    def test_getRawValue(self):
        sensors = "pha", "phb", "doa", "dob", "level", "pressure"
        for s in sensors:
            self.do_get_call('getRawValue', (('sensor', s),))

    def test_Calibration(self):
        """ Try a simple one-point DO calibration, not changing the actual calibration """
        rawvalue = self.app.getRawValue('doa')

        # trycal
        args = (
            ('sensor', 'doa'),
            ('val1', str(rawvalue)),
            ('target1', str(rawvalue))
        )

        self.login()
        self.do_set_call('tryCal', args)

        # savetrialcal
        self.do_set_call('savetrialcal', (('sensor', 'doa'),))

    def test_AutoPilot(self):
        rsp = self.app.call_hello_from_args2("getRecipes", (("loader", "Loading+recipes"),))
        txt = rsp.read().decode('utf-8')
        self.calls_seen.add("getRecipes")
        self._validate_xml_get('getRecipes', txt)

        xml = HelloXML(txt)
        recipes = xml.data.split(',')
        if len(recipes) == 0:
            raise SkipTest("No Recipes")

        preferred = ("light_on_off-looprecipe", "addition_a_slow_1min", "addition_b_slow_1min")
        for r in preferred:
            if r in recipes:
                break
        else:
            r = recipes[0]

        args = (
            ("loader", "Starting+Auto-pilot"),
            ("recipe", r)
        )
        self.login()
        self.do_set_call('runRecipe', args)

        self.do_get_call("getRecipeStep")
        self.do_get_call("getRecipeItems", (("recipe", r),))

        args = (
            ("val1", 'sequence'),
            ("recipe", r)
        )
        self.do_set_call("recipeSkip", args)

    def test_getBatches(self):
        self.do_get_call("getBatches", (("loader", "Loading+batches..."),))

    def test_getReport(self):
        self.do_get_call("getReportTypes", (("loader", "Loading+reports..."),))

    def test_getReportByType(self):
        self.login()
        batches = self.app.getbatches()
        if len(batches.names_to_batches) == 0:
            raise SkipTest("No Batches")

        # get smallest batch
        batch = min(batches.names_to_batches.values(), key=lambda b: b.stop_time - b.start_time)

        id = batch.id
        types = "data", "user_events", "recipe_steps", "errors", "alarms"
        for t in types:
            args = (
                ("mode", 'byBatch'),
                ("type", t),
                ("val1", id),
                ("val2", "")
            )
            self.do_get_call('getReport', args, 'xml', True)

        # by time
        start = batch.start_time
        stop = batch.stop_time
        for t in types:
            args = (
                ("mode", 'byDate'),
                ("type", t),
                ("val1", start),
                ("val2", stop)
            )
            self.do_get_call('getReport', args)

    def test_getPumps(self):
        self.do_get_call("getPumps")

    def test_setpumps(self):
        size = self.app.getmodelsize()
        if size < 80:
            a_speed = 2
        else:
            a_speed = 250

        if size < 500:
            b_speed = c_speed = 2
        else:
            b_speed = c_speed = 500

        args = (
            ("val1", 1),
            ("val2", a_speed)
        )
        self.do_set_call('setpumpa', args)

        args = (
            ("val1", 1),
            ("val2", b_speed)
        )
        self.do_set_call('setpumpb', args)

        args = (
            ("val1", 1),
            ("val2", c_speed)
        )
        self.do_set_call("setpumpc", args)

    def test_setpumpsample(self):
        args = (
            ("val1", "1"),
            ("val2", "0")
        )
        self.do_set_call('setpumpsample', args)

    def test_set(self):

        # cache the initial values to reset at the end
        mv = self.app.getMainValues()

        group = 'agitation'
        mode = "0"
        sp = "20"
        args = (
            ("group", group),
            ("mode", mode),
            ("val1", sp)
        )

        self.do_set_call('set', args)

        ctrl = mv['agitation']
        val = ctrl['sp'] if ctrl['mode'] == 0 else ctrl['man']
        self.app.setag(ctrl['mode'], val)

        group = "temperature"
        mode = "0"
        sp = "37"

        args = (
            ("group", group),
            ("mode", mode),
            ("val1", sp)
        )
        self.do_set_call('set', args)

        ctrl = mv['temperature']
        val = ctrl['sp'] if ctrl['mode'] == 0 else ctrl['man']
        self.app.settemp(ctrl['mode'], val)

        group = "do"
        mode = "1"
        n2 = "25"
        o2 = "150"

        args = (
            ("group", group),
            ("mode", mode),
            ("val1", n2),
            ("val2", o2)
        )
        self.do_set_call("set", args)

        ctrl = mv['do']
        if ctrl['mode'] == 0:
            val1 = ctrl['sp']
            self.app.setdo(ctrl['mode'], val1)
        else:
            val1 = ctrl['manUp']
            val2 = ctrl['manDown']
            self.app.setdo(ctrl['mode'], val1, val2)

        group = "ph"
        mode = "1"
        co2 = "25"
        base = "15"

        args = (
            ("group", group),
            ("mode", mode),
            ("val1", co2),
            ("val2", base)
        )
        self.do_set_call("set", args)

        ctrl = mv['ph']
        if ctrl['mode'] == 0:
            val1 = ctrl['sp']
            self.app.setph(ctrl['mode'], val1)
        else:
            val1 = ctrl['manUp']
            val2 = ctrl['manDown']
            self.app.setph(ctrl['mode'], val1, val2)

    def test_setstartendbatch(self):
        setstartargs = (
            "setstartbatch", (
                ("val1", "autobatchtest"),
            )
        )
        setendargs = (
            "setendbatch", ()
        )

        if self.app.batchrunning():
            order = setendargs, setstartargs
        else:
            order = setstartargs, setendargs

        for call, args in order:
            self.do_set_call(call, args)

    def test_getSensorStates(self):
        self.do_get_call("getSensorStates")

    def test_setSensorState(self):
        args = (
            ("sensor", "phB"),
            ("val1", "0"),
            ("description", "set+sensor+phB+to+state+locked")  # ???????
        )
        self.do_set_call('setSensorState', args)


# auto generate tests
if len(ipaddys) > 1:
    for addy in ipaddys:
        if not addy.strip():
            continue
        src = """
class TestServerCalls_ip%(ip)s(TestServerCalls):
    ipaddy = '%(ip2)s'
        """ % {'ip': addy.replace('.', '_').replace(':', '_'),
                'ip2': addy}
        exec(src)

    # don't actually run the template base class.
    del TestServerCalls
else:
    TestServerCalls.ipaddy = ipaddys[0]


if __name__ == '__main__':
    unittest.main()
    pass
