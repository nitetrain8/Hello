from hello.pid.delay import hours, minutes
import numpy as np
import peakutils


class Fitness2():
    stable_osc_max = 1
    settle_osc_max = 3
    settle_target = 3 * hours
    max_overshoot = 3
    def __init__(self, data=None):
        if data is not None:
            self.calculate(data)
            
    def calculate(self, data):
        x,y,sp = data
        self.settle_time = self.time_stable(x,y,sp)
        self.osc = self.oscillation(x,y,sp)
        self.ovr = np.max(y) - sp
        
    def result_reason(self):
        rv = True
        reason = ""
        if self.settle_time > self.settle_target:
            reason += "Settle %d > %d " % (self.settle_time, self.settle_target)
            rv = False
        if self.osc > self.stable_osc_max:
            reason += "Osc %d > %d " % (int(self.osc), self.stable_osc_max)
            rv = False
        if self.ovr > self.max_overshoot:
            reason += "Ovr %d > %d " % (int(self.ovr), int(self.max_overshoot))
            rv = False
        return rv, reason
    
    def result(self):
        return self.result_reason()[0]
    
    def result2(self):
        s = self.settle_time - self.settle_target
        o = self.stable_osc_max - self.osc
        return s, o
    
    def reason(self):
        return self.result_reason()[1]
        
    def oscillation(self, x, y, sp):
        span = y[10*hours:]
        if not len(span):
            return -1
        ymin = np.min(span)
        ymax = np.max(span)
        return (ymin - ymax) / 2
        
    def time_stable(self, x, y, setpoint):
        hi = setpoint + self.settle_osc_max
        lo = setpoint - self.settle_osc_max
        for t, pv in reversed(list(zip(x,y))):
            if not lo <= pv <= hi:
                break
        return t * 3600 + 1


def damping_ratio(p1, p2, n=1):
    ln = np.log(p1 / p2)
    delta = (1/n) * ln
    z = 1 / (np.sqrt(1+(2*np.pi/delta)**2))
    return z
    
def dr2(ind):
    if not ind.size:
        return 0
    if ind.size == 1:
        return ind[0]
    ratios = []
    for i in range(len(ind)-1):
        ratios.append(damping_ratio(ind[i], ind[i+1]))
    return sum(ratios)/len(ratios)

def time_between(ind):
    if not ind.size:
        return -1
    return np.average(ind[1:]-ind[:-1])

def peaks(x, pv, sp=150, band=5, thresh=0.1):
    hi = sp + band
    lo = sp - band
    t = next((t for t, p in reversed(list(zip(x,pv))) if not lo <= p <= hi),0)
    t = int(t*3600)
    return _peaks(pv, t, len(x), thresh)

def _peaks(x, start, end, thresh=0.5):
    return peakutils.indexes(x[start:end], thres=thresh,min_dist=5*minutes) + start


class Fitness3():
    settle_factor = 1 * hours
    peak_factor = 2 * hours
    ramp_factor = 1.5 * hours
    settle_margin = 3
    damp_factor = 0.1
    
    # The normalizing scale for dampening factor
    # uses an equation of the form a/(b+x*c)-d
    a = 4
    b = 1
    c = 7
    d = 2
    
    def __init__(self, x, y, sp):
        st = self.margin(x,y,sp,self.settle_margin)
        sc = st / self.settle_factor
        self.settle_score = sc
        
        if st >= len(y):
            # no peaks
            self.peak_score = 0
        else:
            ind = _peaks(y, 0, len(y), 0.5)
            if not ind.size:
                ps=-2
            else:
                dr = dr2(ind)
                ps = self.a/(self.b+dr*self.c) - self.d
            mscore = (np.max(y)-sp)/2
            mscore = min(max(0, mscore),5)
            self.peak_score = mscore + ps
        
    def score(self):
        return self.settle_score**2*np.sign(self.settle_score) + \
                self.peak_score**2*np.sign(self.peak_score)
        
    def margin(self, x, y, setpoint, margin):
        hi = setpoint + margin
        lo = setpoint - margin
        for t, pv in reversed(list(zip(x,y))):
            if not lo <= pv <= hi:
                break
        return (t) * 3600 + 1
    
    def __str__(self):
        return "Total:%.2f Peak:%.2f Settle:%.2f" % (self.score(), self.peak_score, self.settle_score)