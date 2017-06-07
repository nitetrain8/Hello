from . import delay

class PIDController():

    AUTO = 0
    MAN = 1
    OFF = 2

    def __init__(self, pgain=1, itime=1, dtime=0, auto_max=100,
                 auto_min=0, beta=1, linearity=1, alpha=0, deadband=0,
                 sp_high=100, sp_low=0, gamma=0, man_request=0, mode=0):

        itime = delay.m2s(itime)
        dtime = delay.m2s(dtime)
        
        self.auto_min = auto_min
        self.auto_max = auto_max
        self.pgain = pgain
        self._itime = itime
        if self._itime:
            self.oneoveritime = 1 / self.itime
        else:
            self.oneoveritime = 0
        self.dtime = dtime
        self.g = gamma
        self.man_request = man_request

        self.bump = 0
        self.last_output = 0
        self.last_err = 0
        self.last_gerr = 0
        self.last_pv = 0
        self.b = beta
        self.l = linearity
        self.a = alpha
        self.deadband = deadband
        self._mode = mode
        
        self.sp_high = sp_high
        self.sp_low = sp_low
        
        self.Uk = self.Up = self.Ui = self.Ud = 0
        
    @property
    def mode(self):
        return self._mode
    
    def set_mode(self, m, pv, sp):
        if m not in (0,1,2):
            raise ValueError(m)
        if m == self._mode:
            return
        elif self._mode == self.OFF and m == self.AUTO:
            self.off_to_auto(pv, sp)
        elif self._mode == self.MAN and m == self.AUTO:
            self.man_to_auto(pv, sp, self.man_request)
        self._mode = m
        
    @property
    def itime(self):
        return self._itime

    @itime.setter
    def itime(self, v):
        self._itime = v
        if v:
            self.oneoveritime = 1 / v
        else:
            self.oneoveritime = 0

    def off_to_auto(self, pv, sp):
        """
        Calculate bump for off-to-auto transfer
        :param pv: current process temp to use for bumpless xfer calculation
        """
        self.man_to_auto(pv, sp, 0)

    def man_to_auto(self, pv, sp, op):
        err_for_pgain = (self.b*sp-pv)*(self.l+(1-self.l)*(abs(self.b*sp-pv))/100)
        err = sp - pv
        uk0 = self.pgain * err_for_pgain
        self.Ui = op - uk0
        self.last_pv = pv
        self.last_err = err
        self.last_ierr = err*self.pgain*self.oneoveritime
        self.last_gerr = self.g * sp - pv
        self.last_berr = self.b * sp - pv
        self.last_output = op
   
    set_bump = man_to_auto

    def reset(self):
        self.Ui = 0
        self.last_pv = 0
        self.last_err = 0
        self.last_ierr = 0
        self.last_berr = 0
    
    def step(self, pv, sp):
        
        if self._mode != 0:
            if self._mode == 1:
                return self.man_request
            elif self._mode == 2:
                return 0
            else:
                raise ValueError(self._mode)
        err = sp - pv
        berr = self.b * sp - pv
        gerr = self.g * sp - pv
        
        # Based on Labview's `PID Get Advanced Error (DBL).vi`
        if self.l == 1 or self.sp_high == self.sp_low:
            nif = 1
        else:
            sp_rng = self.sp_high - self.sp_low
            oml = 1 - self.l

            err = err * (self.l + oml*abs(err)/sp_rng)
            berr = berr * (self.l + oml*abs(berr)/sp_rng)
            gerr = gerr * (self.l + oml*abs(gerr)/sp_rng)
            nif = 1 / (1+10*err*err/ (sp_rng*sp_rng))
        
        ierr = ((err + self.last_err) / 2) * nif * self.pgain * self.oneoveritime
        
        Up = self.pgain * berr
        Ui = self.Ui + ierr
        if 0 < self.a <= 1:
            e = gerr - self.last_gerr
            Ud = -self.pgain * (self.dtime * e) / (1 + self.a * self.dtime * e)
            Ud = (self.Ud - ((self.pgain / self.a) * (gerr - self.last_gerr))) * (self.dtime / (self.dtime + (1 / self.a)))
        else:
            Ud = (gerr - self.last_gerr) * self.pgain * self.dtime 
        Uk = Up + Ui + Ud
        
        # Coercion & back calculation
        # Note Ud isn't involved here.

        # I don't know why. For reference, the 
        # shift register holding Ui is the second
        # from the bottom on the right side in the 
        # Labview Advanced PID vi (directly above
        # the output shift register). The back-
        # calculation is shown when the innermost
        # case statement is "False" in the nest 
        # of Ki related case statements.

        if Uk > self.auto_max:
            Uk = self.auto_max
            Ui = Uk - Up
        elif Uk < self.auto_min:
            Uk = self.auto_min
            Ui = Uk - Up
            
        # XXX debugging
        self.Ui = Ui
        self.Uk = Uk
        self.Ud = Ud
        self.Up = Up
            
        # "Shift Register"
        self.last_output = Uk
        self.last_pv = pv
        self.last_err = err
        self.last_ierr = ierr
        self.last_gerr = gerr
        self.last_berr = berr
        
        return Uk

    def __repr__(self):
        return "Output: %.2f Pgain: %.1f Itime: %.2f" % (self.last_output,
                                                                          self.pgain,
                                                                          self.itime)
    __str__ = __repr__
    

def assert_equal(a,b):
    assert a == b, (a, b)
def test_trap_integration1():
    data = [
        (0, 1, .5),
        (0, 2, 2),
        (0, 3, 4.5)
    ]
    p = PIDController(1,delay.s2m(1))
    for pv, sp, op in data:
        p.Ui -= 1  # counteract effect of increasing set point on Up
        res_op = p.step(pv, sp)
        assert_equal(p.last_err, sp)
        assert_equal(p.Uk, op)
        assert_equal(res_op, op)
test_trap_integration1()

# def check_Ui_backcalc(it, pg, Up, Ud, ierr, accum, val):
#     Ui2 = it * (ierr + accum) * pg
#     Uk2 = Up + Ud + Ui
#     Uk2 = round(Uk2, 8)
#     am = round(val, 8)
#     assert Uk2 == am, (Up, Ud, Ui, Uk2, val)