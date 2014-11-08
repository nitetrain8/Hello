"""

Created by: Nathan Starkweather
Created on: 11/04/2014
Created in: PyCharm Community Edition


"""
from hello.mock.util import nextroutine

__author__ = 'Nathan Starkweather'

from math import sin as _sin, pi as _pi
from time import time as _time
from json import dumps as json_dumps


@nextroutine
def sin_wave(amplitude, period, middle=0, offset=0, gen=None, trigfunc=None):
    """
    @param amplitude: Size of wave (int)
    @param period: period of wave (in units returned from gen)
    @param middle: verticle offset of wave
    @param offset: horizontal offset of wave
    @param gen: infinite iterator. each new value is used to "step" output. default to time().
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

    def __init__(self, name):
        self.pv = 0
        self.name = name
        self._history = []
        self._pvgenerator = lambda: (0, 0)

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

    def todict(self):
        return {'pv': self.pv}


class SimpleController(BaseController):
    def __init__(self, name, pv=0, sp=20, man=5, mode=2, error=0, interlocked=0):

        super().__init__(name)
        self.pv = pv
        self.sp = sp
        self.man = man
        self.mode = mode
        self.error = error
        self.interlocked = interlocked

        self.set_pvgen(sin_wave(5, 30, 15))

    def todict(self):
        return {
            'pv': self.pv,
            'sp': self.sp,
            'man': self.man,
            'mode': self.mode,
            'error': self.error,
            'interlocked': self.interlocked
        }


class TwoWayController(BaseController):
    def __init__(self, name, pv=0, sp=20, manup=5, mandown=0, mode=2, error=0, interlocked=0):
        super().__init__(name)
        self.pv = pv
        self.sp = sp
        self.manup = manup
        self.mandown = mandown
        self.mode = mode
        self.error = error
        self.interlocked = interlocked

        self.set_pvgen(sin_wave(3, 60, 50))

    def todict(self):
        return {
            'pv': self.pv,
            'sp': self.sp,
            'manUp': self.manup,
            'manDown': self.mandown,
            'mode': self.mode,
            'error': self.error,
            'interlocked': self.interlocked
        }


class SmallController(BaseController):
    def __init__(self, name, pv=0, sp=0, mode=0, error=0):
        super().__init__(name)
        self.pv = pv
        self.sp = sp
        self.mode = mode
        self.error = error

        self.set_pvgen(sin_wave(1, 10, 5))

    def todict(self):
        return {
            'pv': self.pv,
            'mode': self.mode,
            'error': self.error
        }

#
# class Agitation(SimpleController):
#     pass
#
#
# class Temperature(SimpleController):
#     pass
#
#
# class pH(TwoWayController):
#     pass
#
#
# class DO(TwoWayController):
#     pass
#
#
# class MainGas(SimpleController):
#     pass


class HelloState():
    def __init__(self):
        self.agitation = a = SimpleController('agitation', 0, 20, 1, 0)
        self.temperature = t = SimpleController('temperature', 30, 37, 0, 0)
        self.ph = ph = TwoWayController('ph', 7, 7.1, 5, 5, 0)
        self.do = d = TwoWayController('do', 50, 70, 15, 150, 0)
        self.maingas = m = SimpleController('maingas', 0, 0, 0.5, 1)
        self.secondaryheat = s = SimpleController('secondaryheat', 30, 37, 0, 0)
        self.level = l = SmallController('level', 3)
        self.filteroven = f = SmallController('condensor', 40, 50)
        self.pressure = p = SmallController('pressure', 0, 0, 0)

        self.controllers = a, t, ph, d, m, s, l, f, p

    def step(self):
        for c in self.controllers:
            c.step()

    def get_raw_main_values(self):
        return {
            "result": "True",
            "message": {c.name: c.todict() for c in self.controllers}
        }

    def jsonify(self):
        return json_dumps(self.get_raw_main_values(), indent=4)

if __name__ == '__main__':
    print(HelloState().jsonify())
