from ..gas_process import HeadspaceProcess, MicroProcess
from ..delay import DelaySink, DelayBuffer

TOTAL_RVOLUME = {
    3: 4,
    15: 17,
    80: 90,
}

# volume fraction of CO2, N2, O2 in air
# note the remaining 1% is trace gasses
AIR_CNO = (0.0004, 0.7809, 0.2095)


class DOProcess():
    """ DO Process
    Uses cascaded calculation model,
    First using HeadspaceProcess to estimate
    headspace gas concentrations, and using
    the result to calculate change in PV. 
    """
    # process gain constant units of  
    # % per delta% per hour 
    # dpv/dt = k*([O2]/0.2095 * 100 - DOPV)
    # where [02] is volume fraction, DOPV is in %
    default_k = 0.1306
    
    # consumption rate constant in units of % per hour
    # presumably, consumption rate is "Constant"
    # within approximation, as long as cellular conditions
    # don't transition between aerobic and anaerobic
    default_c = 0
    
    def __init__(self, main_gas=1, initial_cno=None, reactor_size=80, volume=55, delay=0):
        """
        :param g: gain in units of C/min/%
        :param k: decay rate in units of C/min/dT
        """
        initial_cno = initial_cno or AIR_CNO
        self.sink = DelaySink(delay, initial_cno[2])
        self.delay = self.sink.delay
        
        self.k = 0
        self.k_mult = 1
        self._k = 0
        self.c = 0
        self.dc = 0
        self.d2c = 0
        self.set_values(k=self.default_k)
        
        self._reactor_size = reactor_size
        self._volume = volume
        self.main_gas = main_gas
    
        hs_volume = TOTAL_RVOLUME[reactor_size] - volume
        c, n, o = initial_cno
        self.hp = HeadspaceProcess(hs_volume, c, n, o)

    def apply_ops(self, ops):
        self.set_values(k=ops.k, k_mult=ops.k_mult, c=ops.c, dc=ops.dc, d2c=ops.d2c)
        self._reactor_size = ops.reactor_size
        self.volume = ops.volume
        self.main_gas = ops.main_gas
        self.sink.set_delay(ops.delay)

        c,n,o = ops.initial_actual_cno or AIR_CNO
        self.hp.co2A = c
        self.hp.n2A = n
        self.hp.o2A = o
        self.hp.airA = 1-(c+n+o)

    @property
    def volume(self): 
        return self._volume
    
    def set_values(self, **kw):
        if any(not hasattr(self, a) for a in kw):
            raise KeyError(next(set(kw) - set(dir(self))))
            
        if kw.get('k') is not None or kw.get('k_mult') is not None:
            if kw.get('k') is not None:
                self.k = kw['k'] / 3600
            
            if kw.get('k_mult') is not None:
                self.k_mult = kw['k_mult']
                
            self._k = self.k_mult * self.k
    
        if kw.get('c') is not None:
            self.c = kw['c'] / 3600
        if kw.get('dc') is not None:
            self.dc = kw['dc'] / 3600 / 3600
        if kw.get('d2c') is not None:
            self.d2c = kw['d2c'] / 3600 / 3600 / 3600
            
        if kw.get('delay') is not None:
            self.sink.set_delay(kw['delay'])
    
    @volume.setter
    def volume(self, v):
        self._volume = v
        self.hp.vol = TOTAL_RVOLUME[self._reactor_size] - v

    def step(self, pv, co2_req, n2_req, o2_req, air_req):
        self.hp.calc_gas(self.main_gas, co2_req, n2_req, o2_req, air_req)
        o2 = self.hp.o2A
        o2 = self.delay(o2)
        pvarg = (o2 * 100 / 0.2095 - pv)
        dpv = self._k * pvarg
        pv += dpv
        self.dc += self.d2c
        self.c += self.dc
        pv -= self.c
        if pv < 0:
            return 0
        return pv      

    def getstate(self):
        return {
            'c': self.c*3600,
            'dc': self.dc*3600*3600,
            'd2c': self.d2c*3600*3600*3600,
            'k': self.k,
            'k_mult': self.k_mult
        }
    

class DOProcessMicro():
    """ DO Process with Microsparger support
    Much more complicated than the other model
    but most code is still boilerplate....
    """
    
    def __init__(self, ops=None):
        
        # sane defaults before applying ops
        self.km_hs = 1
        self.km_ms = 1
        self.c = 0
        self.dc = 0
        self.d2c = 0
        
        self.reactor_size = 80
        self.hp = HeadspaceProcess(25, *AIR_CNO)
        self.volume = 55
        self.main_gas = 1

        # These defaults are for the 3L dip tube,
        # which was the first system tested using
        # this method.
        self.m1 = 4.403227 / 3600
        self.m2 = 0.500656 / 3600
        self.m3 = 0.111072 / 3600
        self.b  = 0.445392 / 3600

        if ops is not None:
            self.apply_ops(ops)

    def apply_ops(self, ops):

        def set1(k, m=1,d=1):
            v = getattr(ops, k)
            if v is None:
                return
            setattr(self, k, v*(m/d))

        set1('main_gas')
        set1('km_hs')
        set1('km_ms')
        set1('c', 3600)
        set1('dc', 3600*3600)
        set1('d2c', 3600*3600*3600)
        set1('m1', 1, 3600)
        set1('m2', 1, 3600)
        set1('m3', 1, 3600)
        set1('b',  1, 3600)
        set1('reactor_size')  
        set1('volume')  # must come after reactor size
     
        # handle CNO separately
        c,n,o = ops.initial_actual_cno or AIR_CNO
        self.hp.co2A = c
        self.hp.n2A = n
        self.hp.o2A = o
        self.hp.airA = 1-(c+n+o)

    def get_kla(self, mg, o2):
        hs = self.b + self.m2*mg
        ms = o2 * (self.m1*mg + self.m3)
        return hs, ms

    def getstate(self):
        return {
            'c'  : self.c*3600,
            'dc' : self.dc*3600*3600,
            'd2c': self.d2c*3600*3600*3600,
            'm1' : self.m1*3600,
            'm2' : self.m2*3600,
            'm3' : self.m3*3600,
            'b'  : self.b *3600,
        }
        
    @property
    def volume(self): 
        return self._volume

    @volume.setter
    def volume(self, v):
        self._volume = v
        self.hp.vol = TOTAL_RVOLUME[self.reactor_size] - v
    
    def set_values(self, **kw):
        if any(not hasattr(self, a) for a in kw):
            raise KeyError(next(set(kw) - set(dir(self))))
            
        def set1(v, m=1,d=1):
            if kw.get(v) is not None:
                setattr(self, v, kw[v]*m/d)
        
        set1('c', 3600)
        set1('dc', 3600*3600)
        set1('d2c', 3600*3600*3600)
        set1('m1', 1, 3600)
        set1('m2', 1, 3600)
        set1('m3', 1, 3600)
        set1('b',  1, 3600)
        set1('volume')

    def step(self, pv, co2_req, n2_req, o2_req, air_req):
        self.hp.calc_gas(self.main_gas, co2_req, n2_req, o2_req, air_req)
        o2h = self.hp.o2A

        mg = self.main_gas
        k_ms = self.m1*mg*o2_req + self.m3*o2_req
        k_hs = self.m2*mg + self.b

        k_hs *= self.km_hs
        k_ms *= self.km_ms

        dpv = k_hs * (100/0.2095*o2h - pv) + k_ms*(100/0.2095 - pv)

        pv += dpv
        self.dc += self.d2c
        self.c += self.dc
        pv -= self.c
        if pv < 0:
            return 0
        return pv     