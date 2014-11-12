"""

Created by: Nathan Starkweather
Created on: 11/07/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'


class PIDController():

    # The actual controllers can also be in manual mode,
    # but the PID controller isn't actually aware of it.
    MODE_AUTO = 0
    MODE_OFF = 2

    def __init__(self, set_point=37, pgain=40, itime=33, dtime=0, automax=50,
                 auto_min=0, out_high=100, out_low=0, l=1, b=1, ideal=True):

        self._sp = set_point
        self._pgain = pgain
        self._itime = itime
        if itime:
            self._1overi = 1 / itime
        else:
            self._1overi = 0
        self._dtime = dtime
        self._automax = automax
        self._auto_min = auto_min
        self._out_high = out_high
        self._out_low = out_low
        self._L = l
        self._B = b
        if ideal:
            self.step = self.step_ideal
        else:
            self.step = self.step_nonideal

        self.mode = self.MODE_OFF
        self._accumulated_error = 0
        self._seconds = 0
        self._current_output = 0
        self._bump = 0
        self._last_pv = 0

    def set_on(self, pv, output=0, sp=None):
        """
         Turn the controller back on (aka auto mode).
         In order for the bumpless mechanism to work properly,
         the controller must be made aware of the current pv
         and manual output of the process.
        """
        if sp is not None:
            self._sp = sp
        else:
            sp = self._sp

        self._current_output = output
        self._last_pv = pv

        if self.mode == self.MODE_OFF:
            self._bump = self._current_output - (sp - self._last_pv) * self._pgain
            self.mode = self.MODE_AUTO

    def set_off(self):
        self._bump = 0
        self._current_output = 0
        self._accumulated_error = 0
        self.mode = self.MODE_OFF

    def step_ideal(self, pv):

        # errors
        ep = self._sp - pv
        ei = self._accumulated_error
        ed = pv - self._last_pv

        self._last_pv = pv
        self._accumulated_error += ep

        # itime and dtime terms
        ui = ei * self._1overi
        ud = ed * self._dtime

        Uk = self._bump + self._pgain * (ep + ui + ud)

        if Uk > self._automax:
            Uk = self._automax
        elif Uk < self._auto_min:
            Uk = self._auto_min

        self._current_output = Uk

        return Uk

    def step_nonideal(self, pv):
        # errors
        ep = self._sp - pv
        ei = self._accumulated_error
        ed = pv - self._last_pv

        self._last_pv = pv
        self._accumulated_error += ep

        # itime and dtime terms
        ui = ei * self._1overi
        ud = ed * self._dtime

        Uk = self._bump + self._pgain * ep + ui + ud

        if Uk > self._automax:
            Uk = self._automax
        elif Uk < self._auto_min:
            Uk = self._auto_min

        self._current_output = Uk

        return Uk


from time import time
from collections import deque
from itertools import repeat
from math import exp


def ident(x):
    return x


def delay_buffer(sec, startvalue):
    if not sec:
        # no delay. the internal function hiccups
        # (IndexError: popleft on empty deque) if
        # no delay is passed in.
        return ident

    # you can't send a non-None value to a just-started
    # generator. Therefore, we need a dummy "yield" statement
    # to satisfy that criteria, and then to send the generator
    # the startvalue to initialize the internal state properly.
    # The internal generator state must be suspended between
    # yielding and retriving a value sent by send() to work.
    gen = _delay_generator(sec, startvalue)
    next(gen)
    gen.send(startvalue)
    return gen.send


def _delay_generator(delay, startvalue):
    d = deque(repeat(startvalue, delay - 1), delay)
    pv = startvalue
    d.append(pv)
    yield
    while True:
        rv = d.popleft()
        d.append(pv)
        pv = yield rv


class Model():
    def __init__(self, pv, gain, time_constant, delay):
        self.gain = gain
        self.time_constant = time_constant

        # precalculation. these names just taken from the
        # PID sim spreadsheeet from engineers-excel
        self.a = exp(-1 / time_constant)
        self.b = self.gain * (1 + self.a)

        self.delay = delay_buffer(delay, pv)
        self.pv = pv

    def step(self, ctrl_op):
        newpv = ctrl_op * self.b - self.pv * self.a
        self.pv = self.delay(newpv)
        return self.pv


def process(model, pid):
    """
    @type model: Model
    @type pid: PIDController
    @return:
    """
    pv = model.pv
    while True:
        op = pid.step(pv)
        pv = model.step(op)
        yield op, pv


# The below class is an oops- the lazy ticking mechanism can be applied
# to a complete process, but not to a PID controller (since PV changes, presumably,
# each tick).


class LazyPID(PIDController):
    """ PID controller which calculates values every tick_interval.
     This allows the controller to be used to simulate a PID controller
     which ticks every tick_interval seconds, but doesn't require the caller to
     explicitly keep track of passing time.
    """
    def __init__(self, set_point=37, pgain=40, itime=33, dtime=0, automax=50,
                 auto_min=0, out_high=100, out_low=0, l=1, b=1, ideal=True, tick_interval=1):
        PIDController.__init__(self, set_point, pgain, itime, dtime, automax,
                           auto_min, out_high, out_low, l, b, ideal)

        self._tick_interval = tick_interval
        self._tickfunc = time
        self._lastt = self._tickfunc()

    def tick(self, pv):
        t = self._tickfunc()
        ct = self._lastt

        incr = self._tick_interval

        # tick until ct > t
        while True:
            ct += incr
            if ct > t:
                ct -= incr
                break
            # self.step_main_values()

