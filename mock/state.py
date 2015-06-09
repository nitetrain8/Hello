"""

Created by: Nathan Starkweather
Created on: 11/04/2014
Created in: PyCharm Community Edition


"""
from collections import OrderedDict
from hello.mock.util import nextroutine, HelloXMLGenerator, simple_xml_dump, json_dumps

__author__ = 'Nathan Starkweather'

from math import sin as _sin, pi as _pi
from time import time as _time
from xml.etree.ElementTree import Element, SubElement


@nextroutine
def sin_wave(amplitude, period, middle=0, offset=0, gen=None, trigfunc=None):
    """
    @param amplitude: Size of wave (int)
    @param period: period of wave (in units returned from gen)
    @param middle: verticle offset of wave
    @param offset: horizontal offset of wave
    @param gen: infinite iterator. each new value is used to "step_main_values" output. default to time().
    @param trigfunc: trig function to use in mainloop. default to math.sin().
    """
    if gen is None:
        gen = _time
    pi = _pi
    if trigfunc is None:
        trigfunc = _sin

    pi_over_180 = pi / 180
    start = gen()
    while True:
        t = gen() - start
        result = amplitude * trigfunc((t / period) * pi_over_180 + offset) + middle
        yield t, result


@nextroutine
def simple_wave(xfunc, yfunc):
    """
    @param xfunc: infinite generator accepting no arguments, yielding x values
    @param yfunc: infinite generator accepting a single argument form xfunc, yielding f(x) values
    """
    start = xfunc()
    yield start, yfunc(start)
    while True:
        x = xfunc() - start
        yield x, yfunc(x)


@nextroutine
def multiwave(waves, middle=0):
    """
    @param waves: a list or tuple of wave funcs. waves 'middle' argument
                    must be all be 0 to work properly.
    @param middle: the middle of the waves
    """

    if not waves:
        raise ValueError("Waves is empty")

    # ensure that the waves iterable is a) a container and not a iterator,
    # and b) can't be weirdly modified by passing in a mutable list
    waves = tuple(waves)

    # why did I bother unrolling these loops???
    if len(waves) == 1:
        w = waves[0]
        startx, y = w()
        yield startx, y + middle
        while True:
            x, y = w()
            yield x - startx, y + middle

    # for the loops with multiple waves, only the x value
    # for the *first* function is taken into effect
    # don't abuse this!
    elif len(waves) == 2:
        w1, w2 = waves
        startx, y1 = w1()
        _, y2 = w2()
        yield startx, y1 + y2 + middle
        while True:
            x1, y1 = w1()
            _, y2 = w2()
            yield x1 - startx, y1 + y2 + middle

    elif len(waves) == 3:
        w1, w2, w3 = waves
        startx, y1 = w1()
        _, y2 = w2()
        _, y3 = w3()
        yield startx, middle + y1 + y2 + y3
        while True:
            x, y1 = w1()
            _, y2 = w2()
            _, y3 = w3()
            yield x - startx, middle + y1 + y2 + y3

    # general case.
    # reverse the order of waves so that "startx" and "x" can be
    # reused within the loop body and end up containing the proper
    # values at the end
    rv = middle
    waves = waves[::-1]
    startx = x = 0
    for w in waves:
        startx, y = w()
        rv += y
    yield startx, rv

    while True:
        rv = middle
        waves = waves[::-1]
        for w in waves:
            x, y = w()
            rv += y
        yield x, rv


class BaseController():

    """ Base controller for Backend controllers.
    Controllers know:
     - Their current values
     - The appropriate units for each value (for getMainInfo)
     - How to turn the above into dict objects or Element trees.
    """

    name_to_lv_type = {
        'pv': 'SGL',
        'sp': 'SGL',
        'man': 'SGL',
        'manUp': 'SGL',
        'manDown': 'SGL',
        'mode': 'U16',
        'error': 'U16',
        'interlocked': 'U32'
    }

    def __init__(self, name):
        """
        @param name: Name of controller
        @type name: str
        @return:
        """
        self.name = name
        self._history = []

        # these are just placeholders, and will be overridden
        # by subclasses.
        self.pv = 0
        self._pvgenerator = lambda: (0, 0)
        self.mv_attrs = ("pv",)
        self.mi_attrs = ("pvUnit",)

    def set_pvgen(self, gen):
        self._pvgenerator = gen

    def step(self):
        rv = self._pvgenerator()
        pv = rv[1]
        self.pv = pv
        self._history.append(rv)
        return pv

    def step2(self):
        rv = self._pvgenerator()
        self.pv = rv[1]
        self._history.append(rv)
        return rv  # t, pv

    def mv_todict(self):
        return {'pv': self.pv}

    def mv_todict2(self):
        return OrderedDict((attr, getattr(self, attr)) for attr in self.mv_attrs)

    def mv_toxml(self, root=None):
        if root is None:
            cluster = Element('Cluster')
        else:
            cluster = SubElement(root, 'Cluster')
        cluster.text = '\n'
        cluster.tail = "\n"

        name = SubElement(cluster, "Name")
        name.text = self.name
        name.tail = "\n"
        vals = SubElement(cluster, 'NumElts')
        vals.text = str(len(self.mv_attrs))
        vals.tail = "\n"

        # python unifies number types into a single
        # type, so we have to use a separate mapping
        # to find the proper "type" label to wrap
        # the element in.
        for attr in self.mv_attrs:
            lv_type = self.name_to_lv_type[attr]
            typ = SubElement(cluster, lv_type)
            typ.text = "\n"
            typ.tail = "\n"

            name = SubElement(typ, "Name")
            name.text = attr
            name.tail = "\n"
            val = SubElement(typ, "Val")

            if lv_type == 'SGL':
                val.text = "%.5f" % getattr(self, attr)
            else:
                val.text = "%s" % getattr(self, attr)
            val.tail = "\n"

        return cluster

    def mv_toxml2(self):
        return [(attr, getattr(self, attr)) for attr in self.mv_attrs]

    def mi_toxml(self, root=None):
        if root is None:
            cluster = root = Element('Cluster')
        else:
            cluster = SubElement(root, 'Cluster')
        cluster.text = '\n'
        name = SubElement(cluster, "Name")
        name.text = self.name
        NumElts = SubElement(cluster, "NumElts")
        NumElts.text = str(len(self.mi_attrs))
        for attr in self.mi_attrs:
            val = getattr(self, attr)
            string_ele = SubElement(cluster, "String")
            string_ele.text = '\n'
            name_ele = SubElement(string_ele, "Name")
            name_ele.text = attr
            val_ele = SubElement(string_ele, "Val")
            val_ele.text = val

        return root

    def mi_todict(self):
        return OrderedDict((attr, getattr(self, attr)) for attr in self.mi_attrs)


class StandardController(BaseController):
    def __init__(self, name, pv=0, sp=20, man=5, mode=2, error=0, interlocked=0,
                 pvUnit='', manUnit='', manName=''):

        super().__init__(name)
        self.pv = pv
        self.sp = sp
        self.man = man
        self.mode = mode
        self.error = error
        self.interlocked = interlocked
        self.pvUnit = pvUnit
        self.manUnit = manUnit
        self.manName = manName

        self.mv_attrs = 'pv', 'sp', 'man', 'mode', 'error', 'interlocked'
        self.mi_attrs = 'pvUnit', 'manUnit', 'manName'

        self.set_pvgen(sin_wave(5, 30, 15))

    def mv_todict(self):
        return {
            'pv': self.pv,
            'sp': self.sp,
            'man': self.man,
            'mode': self.mode,
            'error': self.error,
            'interlocked': self.interlocked
        }


class TwoWayController(BaseController):
    def __init__(self, name, pv=0, sp=20, manup=5, mandown=0, mode=2, error=0, 
                 interlocked=0, pvUnit='', manUpUnit='', manDownUnit='', manUpName='',
                 manDownName=''):
        BaseController.__init__(self, name)
        self.pv = pv
        self.sp = sp
        self.manUp = manup
        self.manDown = mandown
        self.mode = mode
        self.error = error
        self.interlocked = interlocked
        self.pvUnit = pvUnit
        self.manUpUnit = manUpUnit
        self.manDownUnit = manDownUnit
        self.manUpName = manUpName
        self.manDownName = manDownName

        self.mv_attrs = 'pv', 'sp', 'manUp', 'manDown', 'mode', 'error', 'interlocked'
        self.mi_attrs = 'pvUnit', 'manUpUnit', 'manDownUnit', 'manUpName', 'manDownName'

        self.set_pvgen(sin_wave(3, 60, 50))

    def mv_todict(self):
        return {
            'pv': self.pv,
            'sp': self.sp,
            'manUp': self.manUp,
            'manDown': self.manDown,
            'mode': self.mode,
            'error': self.error,
            'interlocked': self.interlocked
        }


class SmallController(BaseController):
    def __init__(self, name, pv=0, sp=0, mode=0, error=0, pvUnit=""):
        BaseController.__init__(self, name)
        self.pv = pv
        self.sp = sp
        self.mode = mode
        self.error = error
        self.pvUnit = pvUnit

        self.mv_attrs = 'pv', 'mode', 'error'
        self.mi_attrs = 'pvUnit',

        self.set_pvgen(sin_wave(1, 10, 5))

    def mv_todict(self):
        return {
            'pv': self.pv,
            'mode': self.mode,
            'error': self.error
        }


class AgitationController(StandardController):
    def __init__(self, pv=0, sp=20, man=5, mode=2, error=0, interlocked=0):
        StandardController.__init__(self, "Agitation", pv, sp, man, mode, error, interlocked)
        self.pvUnit = "RPM"
        self.manUnit = "%"
        self.manName = "Percent Power"
        self.mv_attrs = tuple(a for a in self.mv_attrs if a != 'interlocked')


class TemperatureController(StandardController):
    def __init__(self, pv=0, sp=20, man=5, mode=2, error=0, interlocked=0):
        StandardController.__init__(self, "Temperature", pv, sp, man, mode, error, interlocked)
        self.pvUnit = "\xb0C"
        self.manUnit = "%"
        self.manName = "Heater Duty"


class pHController(TwoWayController):
    def __init__(self, pv=0, sp=20, manup=5, mandown=0, mode=2, error=0, interlocked=0):
        TwoWayController.__init__(self, "pH", pv, sp, manup, mandown, mode, error, interlocked)
        self.pvUnit = ""
        self.manUpUnit = "%"
        self.manDownUnit = "%"
        self.manUpName = "Base"
        self.manDownName = "CO_2"
        self.mv_attrs = tuple(a for a in self.mv_attrs if a != 'interlocked')


class DOController(TwoWayController):
    def __init__(self, pv=0, sp=20, manup=5, mandown=0, mode=2, error=0, interlocked=0):
        TwoWayController.__init__(self, "DO", pv, sp, manup, mandown, mode, error, interlocked)
        self.pvUnit = "%"
        self.manUpUnit = "mL/min"
        self.manDownUnit = "%"
        self.manUpName = "O_2"
        self.manDownName = "N_2"
        self.mv_attrs = tuple(a for a in self.mv_attrs if a != 'interlocked')


class MainGasController(StandardController):
    def __init__(self, pv=0, sp=0, mode=0, error=0, interlocked=0):
        StandardController.__init__(self, "MainGas", pv, sp, mode, error, interlocked)
        self.pvUnit = "L/min"
        self.manUnit = "L/min"
        self.manName = "Total Flow"
        self.mv_attrs = tuple(a for a in self.mv_attrs if a != 'sp')


class LevelController(SmallController):
    def __init__(self, pv=0, sp=0, mode=0, error=0):
        SmallController.__init__(self, "Level", pv, sp, mode, error)
        self.pvUnit = "L"


class FilterOvenController(SmallController):
    def __init__(self, pv=0, sp=0, mode=0, error=0):
        SmallController.__init__(self, "Condenser", pv, sp, mode, error)
        self.pvUnit = "\xb0C"


class PressureController(SmallController):
    def __init__(self, pv=0, sp=0, mode=0, error=0):
        SmallController.__init__(self, "Pressure", pv, sp, mode, error)
        self.pvUnit = "psi"


class SecondaryHeatController(StandardController):
    def __init__(self, pv=0, sp=0, mode=0, error=0, interlocked=0):
        StandardController.__init__(self, "SecondaryHeat", pv, sp, mode, error, interlocked)
        self.pvUnit = "\xb0C"
        self.manUnit = "%"
        self.manName = "Heater Duty"


class HelloStateError(Exception):
    pass


class AuthError(HelloStateError):
    """ generic permissions error """
    pass


class LoginError(AuthError):
    """ specifically, bad username/password
    """


from time import time


version_info = OrderedDict((
    ("RIO", "V12.1"),
    ("Server", "V3.1"),
    ("Model", "PBS 3"),
    ("Database", "V2.2"),
    ("Serial Number", "01459C77"),
    ("Magnetic Wheel", True)
))


class HelloState():

    def __init__(self):
        self.agitation = a = AgitationController(0, 20, 1, 0, 0, 0)
        self.temperature = t = TemperatureController(30, 37, 0, 0, 0, 0)
        self.ph = ph = pHController(7, 7.1, 5, 5, 0)
        self.do = d = DOController(50, 70, 15, 150, 0)
        self.maingas = m = MainGasController(0, 0, 0.5, 1)
        self.secondaryheat = sh = SecondaryHeatController(30, 37, 0, 0)
        self.level = l = LevelController(3)
        self.filteroven = f = FilterOvenController(40, 50)
        self.pressure = p = PressureController(0, 0, 0)

        self._mv_controller_array = a, t, sh, d, ph, p, l, f, m
        self._mi_controller_array = a, t, d, ph, p, l, f, sh, m

        self._login_info = {
            'user1': '12345',
            'pbstech': '727246',
            'webuser1': '1'
        }
        self._logged_in = False
        self._last_login = 0

        self._version_info = version_info.copy()
        self.true_reply_xml_encoding = "windows-1252"

        self.xml_gen = HelloXMLGenerator()

    def step_main_values(self):
        for c in self._mv_controller_array:
            c.step()

    def get_dict_main_values(self):
        return OrderedDict((
            ("result", "True"),
            ("message", OrderedDict((c.name.lower(), c.mv_todict2()) for c in self._mv_controller_array))
        ))

    def get_update(self, json=True):
        self.step_main_values()
        return self.getMainValues(json)

    def get_xml_main_values(self):

        # I don't know why, but the server reply for the
        # real hello webserver returns main value controllers
        # in a different order if xml vs json is requested.
        # 4-15-15: XML is created via dump to string, JSON by format
        # existing string template.

        message = [(c.name, c.mv_toxml()) for c in self._mv_controller_array if c.name != 'SecondaryHeat']
        message.append((self.secondaryheat.name, self.secondaryheat.mv_toxml()))
        return self.xml_gen.hello_tree_from_msg(message, "Message")

    def getMainValues(self, json=True):
        if json:
            return json_dumps(self.get_dict_main_values())
        else:
            return self.xml_gen.tree_to_xml(self.get_xml_main_values(), 'windows-1252')

    def login(self, val1, val2, loader, skipvalidate):
        user = val1  # clarity
        pwd = val2  # clarity
        missing = object()
        if self._login_info.get(user.lower(), missing) == pwd:
            self._logged_in = True
            self._last_login = time()
            return True
        return False

    def logout(self):
        self._logged_in = False
        return True

    def getversion(self, json=False):

        message = self._version_info
        if json:
            reply = OrderedDict((
                ("result", "True"),
                ("message", message)
            ))
            rv = json_dumps(reply)
        else:
            rv = self.xml_gen.create_hello_xml(message, "Versions",
                                               "True", self.true_reply_xml_encoding)

        return rv

    def getmaininfo(self, json=False):
        message = OrderedDict((c.name, c.mi_todict()) for c in self._mi_controller_array)
        message['BioReactorModel'] = self._version_info['Model']
        message.move_to_end('SecondaryHeat')
        message.move_to_end('MainGas')
        if json:
            msg = json_dumps(OrderedDict((
                ("result", "True"),
                ("message", message)
            )))

            return msg.encode('utf-8')
        else:
            return self.xml_gen.create_hello_xml(message, "Message", "True", self.true_reply_xml_encoding)


def test1():
    from xml.etree.ElementTree import XML
    xml = HelloState().getMainValues(False)
    xml = XML(xml)
    for line in simple_xml_dump(xml).split():
        print(line)
    # dump(xml)

if __name__ == '__main__':
    test1()
