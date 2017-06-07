from ..gas_process import HeadspaceProcess
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
    
    def __init__(self, main_gas=1, initial_pv=60, initial_cno=None, reactor_size=80, volume=55, delay=0):
        """
        :param g: gain in units of C/min/%
        :param k: decay rate in units of C/min/dT
        """
        initial_cno = initial_cno or AIR_CNO
        self.sink = DelaySink(delay, initial_cno[2])
        self.delay = self.sink.delay
        
        self.k = 0
        self.k_mult = 0
        self._k = 0
        self.c = 0
        self.dc = 0
        self.d2c = 0
        self.set_values(k=self.default_k, k_mult=1, c=self.default_c, dc=0, d2c=0)
        
        self._reactor_size = reactor_size
        self._volume = volume
        self.main_gas = main_gas
    
        hs_volume = TOTAL_RVOLUME[reactor_size] - volume
        c, n, o = initial_cno
        self.hp = HeadspaceProcess(hs_volume, c, n, o)
        
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
    

