class HeadspaceProcess():
    def __init__(self, vol, co2A=0, n2A=0.78, o2A=0.21):
        """ 
        vol: volume headspace (L)
        main_gas: main gas flow rate (L/min)
        co2: CO2 request (%)
        n2: N2 request (%)
        
        Calculate headspace concentration. DT = 1 second. 
        """
        self.vol = vol
        self.co2A = co2A
        self.n2A = n2A
        self.o2A = o2A
        self.airA = 1 - (co2A+n2A+o2A)
        
    def step(self, main_gas, co2_req, n2_req, o2_req, air_req):
        self.calc_gas(main_gas, co2_req, n2_req, o2_req, air_req)
        return self.o2A
    
    def calc_gas(self, main_gas, co2_req, n2_req, o2_req, air_req):
        """ 
        Calculate new headspace gas concentration.
        Assumptions:
            - Mixing time is 0 seconds, i.e. gas mixture is always perfectly mixed
            - Gas lost from headspace is always equal to gas entering headspace
            - Concentration of individual gasses lost match headspace concentration of gasses. 
            - Mass transfer coefficient of Air <-> liquid k <<< Mg (no volume lost due to absorption to liquid)
            - Air O2: 20.95%, N2: 78.09%, CO2=0.04%, other = 1-(o2+n2+co2)
        """
        
        # If headspace volume is very low, assume that the actual gas concentration is 0
        # This keeps the model from crashing when volume shrinks due to e.g. base added
        if self.vol < 1e-5:
            self.co2A = 0
            self.n2A = 0
            self.o2A = 0
            self.airA = 0
            return

        mg = main_gas / 60
        
        # volume of gas lost
        co2L = mg * self.co2A
        n2L = mg * self.n2A
        o2L = mg * self.o2A
        airL = mg * self.airA
        
        # volume of gas gained
        # airG is non-corrected volume of air added
        co2G = mg * co2_req
        n2G = mg * n2_req
        o2G = mg * o2_req
        airG = mg * air_req
        
        # air contribution to gases
        # airG is corrected to reflect
        # the volume of non-tracked gases
        # ie the 1% of trace elements or so
        co2G += 0.0004 * airG
        o2G += 0.2095 * airG
        n2G += 0.7809 * airG
        airG = .0092 * airG
        
        # new volume of each gas
        co2V = co2G - co2L + self.co2A * self.vol
        n2V = n2G - n2L + self.n2A * self.vol
        o2V = o2G - o2L + self.o2A * self.vol
        airV = airG - airL + self.airA * self.vol
        
        # finally, new percentages
        self.co2A = co2V / self.vol
        self.n2A = n2V / self.vol
        self.o2A = o2V / self.vol
        self.airA = airV / self.vol
        
        # Uncomment to perform sanity checks
        # Errors should be on the order of 
        # floating point rounding error ~1e-14
        # self._err_ = self.vol - sum((co2V, n2V, o2V, airV))
        # self._err2_ = 1 - (self.co2A + self.n2A + self.o2A + self.airA)
        # self._err3_ = (co2L+n2L+o2L+airL) - (co2G + n2G + o2G + airG)
        
    @staticmethod
    def actual_from_request(co2, n2, o2, air):
        total = co2 + n2 + o2 + air
        co2 /= total
        n2 /= total
        o2 /= total
        air /= total
        
        co2 += 0.0004 * air
        n2 += 0.7809 * air
        o2 += 0.2095 * air
        air = 1 - (co2+n2+o2)
        return co2, n2, o2, air
            

class GasController():
    def __init__(self, co2mfcmax, n2mfcmax, o2mfcmax, airmfcmax):
        self.cm = co2mfcmax
        self.nm = n2mfcmax
        self.om = o2mfcmax
        self.am = airmfcmax
        self.mg_max = max((self.cm, self.nm, self.om, self.am))
   
    def request(self, main_gas, co2_req, n2_req, o2_req):

        if main_gas > self.mg_max: main_gas = self.mg_max
        co2_req_max = 1
        if co2_req > co2_req_max: co2_req = co2_req_max
        co2max = self.cm / main_gas
        co2pc = co2max if co2_req > co2max else co2_req

        o2_req_max = 1 - co2pc
        if o2_req > o2_req_max: o2_req = o2_req_max
        o2max = self.om / main_gas
        o2pc = o2max if o2_req > o2max else o2_req
        
        n2_req_max = 1 - co2pc - o2pc
        if n2_req > n2_req_max: n2_req = n2_req_max
        n2max = self.nm / main_gas
        n2pc = n2max if n2_req > n2max else n2_req
        
        apc = 1 - co2pc - o2pc - n2pc
        return co2pc, n2pc, o2pc, apc

# Test code
def _round(dig, *args):
    rv = []
    for a in args:
        rv.append(round(a, dig))
    return rv

def test_gas_controller():
    ctrl = GasController(1, 10, 2, 10)
    
    c,o,n = (0.8, 0.3, 1)
    rc, rn, ro, ra = _round(5, *ctrl.request(0.5, c,n,o))
    assert rc == 0.8, rc
    assert ro == 0.2, ro
    assert rn == 0, rn
    assert ra == 0, ra
    
    rc, rn, ro, ra = _round(5, *ctrl.request(10, c,n,o))
    assert rc == 0.1, rc
    assert ro == 0.2, ro
    assert rn == 0.7, rn
    assert ra == 0, ra
    
    c,o,n = (0.8, 0, 1)
    rc, rn, ro, ra = _round(5, *ctrl.request(10, c,n,o))
    assert rc == 0.1, rc
    assert ro == 0, ro
    assert rn == 0.9, rn
    assert ra == 0, ra
    
    c,o,n = (0.07, 0.1, 0.3)
    rc, rn, ro, ra = _round(5, *ctrl.request(10, c,n,o))
    assert rc == 0.07, rc
    assert ro == 0.1, ro
    assert rn == 0.3, rn
    assert ra == 0.53, ra
    
    for mg in (0.5, 1, 5, 10):
        for c in 0.1, 0.5, 0.8, 1:
            for o in 0.1, 0.5, 0.8, 1:
                for n in 0.1, 0.5, 0.8, 1:
                    args = (mg, c, n, o)
                    ec = round(min(1/mg, c), 5)
                    eo = round(min(2/mg, (1-ec), o),5)
                    en = round(min(1-ec-eo, n),5)
                    ea = round(1-ec-eo-en,5)
                    rc, rn, ro, ra = _round(5, *ctrl.request(*args))
                    assert rc == ec, (rc, ec, args)
                    assert ro == eo, (ro, eo, args, (rc, rn, ro, ra))
                    assert rn == en, (rn, en, args)
                    assert ra >= 0 and ra == ea, (ra, ea, args)
    
test_gas_controller()