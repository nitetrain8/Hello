"""

Created by: Nathan Starkweather
Created on: 11/04/2014
Created in: PyCharm Community Edition


"""
from hello.mock.util import nextroutine, xml_tostring, simple_xml_dump, obj_to_xml

__author__ = 'Nathan Starkweather'

from math import sin as _sin, pi as _pi
from time import time as _time
from json import dumps as json_dumps
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
        result = amplitude * trigfunc((t % period) * pi_over_180 + offset) + middle
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
        self.mi_attrs = ("pvunit",)

    def mi_toxml(self):
        pass

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
        return {attr: getattr(self, attr) for attr in self.mv_attrs}

    def mv_toxml(self, root=None):
        if root is None:
            cluster = Element('Cluster')
        else:
            cluster = SubElement(root, 'Cluster')
        cluster.text = '\n'

        name = SubElement(cluster, "Name")
        name.text = self.name.capitalize()
        vals = SubElement(cluster, 'NumElts')
        vals.text = str(len(self.mv_attrs))

        # python unifies number types into a single
        # type, so we have to use a separate mapping
        # to find the proper "type" label to wrap
        # the element in.
        for attr in self.mv_attrs:
            lv_type = self.name_to_lv_type[attr]
            typ = SubElement(cluster, lv_type)
            typ.text = "\n"

            name = SubElement(typ, "Name")
            name.text = attr
            val = SubElement(typ, "Val")

            if lv_type == 'SGL':
                val.text = "%.5f" % getattr(self, attr)
            else:
                val.text = "%s" % getattr(self, attr)

        return cluster


class StandardController(BaseController):
    def __init__(self, name, pv=0, sp=20, man=5, mode=2, error=0, interlocked=0,
                 pvunit='', manunit='', manname=''):

        super().__init__(name)
        self.pv = pv
        self.sp = sp
        self.man = man
        self.mode = mode
        self.error = error
        self.interlocked = interlocked
        self.pvunit = pvunit
        self.manunit = manunit
        self.manname = manname

        self.mv_attrs = 'pv', 'sp', 'man', 'mode', 'error', 'interlocked'

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
                 interlocked=0, pvunit='', manupunit='', mandownunit='', manupname='',
                 mandownname=''):
        BaseController.__init__(self, name)
        self.pv = pv
        self.sp = sp
        self.manUp = manup
        self.manDown = mandown
        self.mode = mode
        self.error = error
        self.interlocked = interlocked
        self.pvpunit = pvunit
        self.manupunit = manupunit
        self.mandownunit = mandownunit
        self.manupname = manupname
        self.mandownname = mandownname

        self.mv_attrs = 'pv', 'sp', 'manUp', 'manDown', 'mode', 'error', 'interlocked'

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
    def __init__(self, name, pv=0, sp=0, mode=0, error=0, pvunit=""):
        BaseController.__init__(self, name)
        self.pv = pv
        self.sp = sp
        self.mode = mode
        self.error = error
        self.pvunit = pvunit

        self.mv_attrs = 'pv', 'mode', 'error'

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
        self.pvunit = "RPM"
        self.manunit = "%"
        self.manname = "Power"


class TemperatureController(StandardController):
    def __init__(self, pv=0, sp=20, man=5, mode=2, error=0, interlocked=0):
        StandardController.__init__(self, "Temperature", pv, sp, man, mode, error, interlocked)
        self.pvunit = "\xb0C"
        self.manunit = "%"
        self.manname = "Heater Duty"


class pHController(TwoWayController):
    def __init__(self, pv=0, sp=20, manup=5, mandown=0, mode=2, error=0, interlocked=0):
        TwoWayController.__init__(self, "pH", pv, sp, manup, mandown, mode, error, interlocked)
        self.pvunit = "pH"
        self.manupunit = "%"
        self.mandownunit = "%"
        self.manupname = "Base"
        self.mandownname = "CO_2"


class DOController(TwoWayController):
    def __init__(self, pv=0, sp=20, manup=5, mandown=0, mode=2, error=0, interlocked=0):
        TwoWayController.__init__(self, "DO", pv, sp, manup, mandown, mode, error, interlocked)
        self.pvunit = "%"
        self.manupunit = "mL/min"
        self.mandownunit = "%"
        self.manupname = "O_2"
        self.mandownname = "N_2"


class MainGasController(StandardController):
    def __init__(self, pv=0, sp=0, mode=0, error=0, interlocked=0):
        StandardController.__init__(self, "MainGas", pv, sp, mode, error, interlocked)
        self.pvunit = ""
        self.manunit = "L/min"
        self.manname = "Gas Flow"


class LevelController(SmallController):
    def __init__(self, pv=0, sp=0, mode=0, error=0):
        SmallController.__init__(self, "Level", pv, sp, mode, error)
        self.pvunit = "L"


class FilterOvenController(SmallController):
    def __init__(self, pv=0, sp=0, mode=0, error=0):
        SmallController.__init__(self, "Condensor", pv, sp, mode, error)
        self.pvunit = "\xb0C"


class PressureController(SmallController):
    def __init__(self, pv=0, sp=0, mode=0, error=0):
        SmallController.__init__(self, "Pressure", pv, sp, mode, error)
        self.pvunit = "psi"


class SecondaryHeatController(StandardController):
    def __init__(self, pv=0, sp=0, mode=0, error=0, interlocked=0):
        StandardController.__init__(self, "SecondaryHeat", pv, sp, mode, error, interlocked)
        self.pvunit = "\xb0C"
        self.manunit = "%"
        self.manname = "Power"


class HelloStateError(Exception):
    pass


class AuthError(HelloStateError):
    """ generic permissions error """
    pass


class LoginError(AuthError):
    """ specifically, bad username/password
    """


from time import time


version_info = {
    "RIO": "V12.1",
    "Server": "V3.1",
    "Model": "PBS 3",
    "Database": "V2.2",
    "Serial Number": "01459C77"
}


class HelloState():
    def __init__(self):
        self.agitation = a = AgitationController(0, 20, 1, 0, 0, 0)
        self.temperature = t = TemperatureController(30, 37, 0, 0, 0, 0)
        self.ph = ph = pHController(7, 7.1, 5, 5, 0)
        self.do = d = DOController(50, 70, 15, 150, 0)
        self.maingas = m = MainGasController(0, 0, 0.5, 1)
        self.secondaryheat = s = SecondaryHeatController(30, 37, 0, 0)
        self.level = l = LevelController(3)
        self.filteroven = f = FilterOvenController(40, 50)
        self.pressure = p = PressureController(0, 0, 0)

        # the short local names are for brevity.
        self.controllers = a, t, ph, d, m, s, l, f, p

        self._login_info = {
            'user1': '12345',
            'pbstech': '727246'
        }
        self._logged_in = False
        self._last_login = 0

        self._version_info = version_info.copy()

    def step_main_values(self):
        for c in self.controllers:
            c.step()

    def get_dict_main_values(self):
        return {
            "result": "True",
            "message": {c.name: c.mv_todict2() for c in self.controllers}
        }

    def get_update(self, json=True):
        self.step_main_values()
        return self.getMainValues(json)

    def get_xml_main_values(self):
        # Yes, XML really is this goddamn stupid
        # SubElement and c.mv_toxml modify state in-place.
        root = Element("Reply")
        root.text = ""
        result = SubElement(root, 'Result')
        result.text = "True"
        message = SubElement(root, "Message")
        message.text = ""
        cluster = SubElement(message, "Cluster")
        cluster.text = ""
        name = SubElement(cluster, "Name")
        name.text = "Message"
        nelements = SubElement(cluster, "NumElts")
        nelements.text = str(len(self.controllers))
        for c in self.controllers:
            c.mv_toxml(cluster)
        return root

    def getMainValues(self, json=True):
        if json:
            return json_dumps(self.get_dict_main_values(), indent="\t")
        else:
            return xml_tostring(self.get_xml_main_values(), None, 'ascii')

    def login(self, val1, val2, loader, skipvalidate):
        user = val1
        pwd = val2
        if self._login_info[user.lower()] == pwd:
            self._logged_in = True
            self._last_login = time()
            return True
        return False

    def logout(self):
        self._logged_in = False
        return True

    def getversion(self, json=False):
        reply = {
            "Result": "True",
            "Message": {
                "Versions": self._version_info
            }
        }

        if json:
            rv = json_dumps(reply)
        else:
            rv = obj_to_xml(reply, "Versions")

        return rv



def test1():
    from xml.etree.ElementTree import XML
    xml = HelloState().getMainValues(False)
    xml = XML(xml)
    for line in simple_xml_dump(xml).split():
        print(line)
    # dump(xml)

if __name__ == '__main__':
    test1()
