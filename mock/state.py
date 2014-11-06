"""

Created by: Nathan Starkweather
Created on: 11/04/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from math import sin as _sin, pi as _pi
from time import time as _time
from functools import wraps


def nextroutine(f):

    @wraps(f)
    def wrapper(*args, **kwargs):
        g = f(*args, **kwargs)
        return g.__next__
    return wrapper


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
        t = gen()
        result = amplitude * trigfunc(((t - start) % period) * pi_over_180 + offset) + middle
        yield result


@nextroutine
def multiwave(waves, middle=0):
    """
    @param waves: a list or tuple of sin_waves. sin_waves 'middle' argument
                    must be all be 0 to work properly.
    @param middle: the middle of the waves
    """

    if not waves:
        raise ValueError("Waves is empty")

    # why???
    if len(waves) == 1:
        w = waves[0]
        while True:
            rv = middle
            yield rv + w()

    elif len(waves) == 2:
        w1, w2 = waves
        while True:
            rv = middle
            yield rv + w1() + w2()

    elif len(waves) == 3:
        w1, w2, w3 = waves
        while True:
            rv = middle
            yield rv + w1() + w2() + w3()

    # else
    while True:
        rv = middle
        for w in waves:
            rv += w()
        yield rv


class BaseController():

    def __init__(self, name):
        self.name = name
        self._history = []
        self._pvgenerator = lambda: 0

    def set_pvgen(self, gen):
        self._pvgenerator = gen

    def step(self):
        rv = self._pvgenerator()
        self._history.append(rv)
        return rv

    def todict(self):
        return {}


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

    def todict(self):
        return {c.name: c.todict() for c in self.controllers}

if __name__ == '__main__':
    HelloState()
