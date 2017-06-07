from decimal import Decimal as D
from collections import deque

__all__ = "seconds minutes hours days m2s s2m h2s DelayBuffer DelaySink".split()

seconds = 1
minutes = seconds * 60
hours = minutes * 60
days = hours * 24

def m2s(m):
    return m*60
def s2m(s):
    return s/60
def h2s(h):
    return m2s(h*60)


class DelayBuffer(deque):
    def __init__(self, delay=30, startvalue=0):
        delay = int(delay)
        self.delay = delay
        super().__init__(startvalue for _ in range(delay + 1))

    def cycle(self, hd):
        self[0] = hd
        self.rotate(1)
        return self[0]
  

class DelaySink():
    def __init__(self, delay, initial, pc_decay=0.95):
        assert 0 < pc_decay <= 1, "don't be a retard"
        self.df = self.calc_df(delay, pc_decay)
        if delay:
            #self.sink = (self.df + initial) / self.df # fill the sink
            self.sink = initial * (1-self.df) / self.df
        else:
            self.sink = 0
        self._delay = delay
        self._pc = pc_decay
        
    def calc_df(self, delay, pc):
        if not delay:
            return 1
        # Attempt to be precise by temporarily using decimal.Decimal
        # to perform the math
        one = D(1)
        return float(one - (one - D(pc))**(one / D(delay)))
        
    def set_delay(self, delay):
        self.df = self.calc_df(delay, self._pc)
        self._delay = delay
        
    def delay(self, op):
        self.sink += op
        dNdt = self.sink*self.df
        self.sink -= dNdt
        return dNdt