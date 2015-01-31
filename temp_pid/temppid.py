"""

Created by: Nathan Starkweather
Created on: 10/09/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from hello.hello import HelloApp
from hello.logger import PLogger
from time import time, sleep
from officelib.xllib.xladdress import cellRangeStr
import traceback


class TPIDBadError(Exception):
    pass


class Runner(PLogger):
    def __init__(self, ps, its, ds, sps, app_or_ipv4='192.168.1.4'):
        self.app_or_ipv4 = app_or_ipv4
        PLogger.__init__(self, "PID Test Runner")
        self.combos = [(p, i, d, sp) for p in ps for i in its for d in ds for sp in sps]

        if not self.combos:
            raise ValueError("Must have at least one test")

    def init_app(self):
        if isinstance(self.app_or_ipv4, HelloApp):
            return self.app_or_ipv4
        else:
            return HelloApp(self.app_or_ipv4)

    def run(self, p, i, d, sp, app, auto_max=50, agitation=(0, 28)):
        """
        @type app: HelloApp
        """
        self._log("Running test:", p, i, d, sp)
        r = PIDTest(p, i, d, sp, app, auto_max, agitation)
        try:
            r.run()
        except:
            self._log_err("Error running test")
        return r

    def runall(self):
        app = self.init_app()
        self._runs = []
        try:
            for p, i, d, sp in self.combos:
                try:
                    r = self.run(p, i, d, sp, app, 100, None)
                except:
                    self._log_err("Error running test")
                else:
                    self._runs.append(r)
                finally:
                    app.login()
                    app.settemp(0, 30)
                    while app.gettemppv() > 31:
                        self._log("Waiting for temp to fall")
                        sleep(60)
        finally:
            # no exception ever!
            self._log("Attempting to shutdown")
            while True:
                try:
                    app.login()
                    app.settemp(0, 37)
                    break
                except:
                    self._log_err("Oh no!")
                    app.reconnect()
            self._log("Shutdown!")

    def plotall(self):
        from officelib.xllib.xlcom import xlObjs
        xl, wb, ws, cells = xlObjs()
        for i, r in enumerate(self._runs, 1):
            r.plot(ws, i * 3 - 2)


class PIDTest(PLogger):
    """ PID test runner/plotter

    @type xrng: str
    @type yrng: str

    """

    _passmap = {
        "No": False,
        "Yes": True,
        True: True,
        False: False,
        1: True,
        0: False
    }

    app = None

    def __init__(self, p, i, d, sp, app_or_ipv4='192.168.1.6', auto_max=50,
                 agitation=(0, 20)):
        """
        @param p: pgain
        @type p: int | float | decimal.Decimal | str
        @param i: itime
        @type i: int | float | decimal.Decimal | str
        @param d: dtime
        @type d: int | float | decimal.Decimal | str
        @param sp: set point
        @type sp: int | float | decimal.Decimal | str
        @param app_or_ipv4: HelloApp object, or IPV4 to pass to HelloApp constructor
        @type app_or_ipv4: str | HelloApp
        """
        PLogger.__init__(self, "PIDTest %s%s%s%s" % (p, i, d, sp))
        self.xrng = None
        self.yrng = None
        self.p = p
        self.i = i
        self.d = d
        self.sp = sp
        self.passed = False
        self.data = None
        self.pvs = None
        self.auto_max = auto_max
        self.agitation = agitation

        if type(app_or_ipv4) is HelloApp:
            self.app = app_or_ipv4
        else:
            self.app = HelloApp(app_or_ipv4)

    def can_begin(self, mv):

        if mv['temperature']['interlocked']:
            return False
        return True

    def _init_settings(self):

        app = self.app
        settings = (
            ("Temperature", "P_Gain_(%/C)", self.p),
            ("Temperature", "I_Time_(min)", self.i),
            ("Temperature", "D_Time_(min)", self.d),
            ("Temperature", "Heat Auto Max (%)", self.auto_max)
        )
        for grp, set, val in settings:
            app.login()
            self._log("Setting %s %s to %s" % (grp, set, val))
            app.setconfig(grp, set, val)

    def run(self, margin=0.1, settle_time=3600, poll_interval=10, ramp_timeout=7200):
        """
        @param margin: SP +/- margin to begin "settling"
        @type margin: int | float
        @param settle_time: seconds to keep polling after reaching temp +/- settle_margin
        @type settle_time: int
        """

        # Initialize bioreactor setting state
        self._log("Initializing settings")
        self._init_settings()
        app = self.app
        sp = self.sp
        pvs = self.pvs = []
        _time = time
        _sleep = sleep
        timeout_time = ramp_timeout + _time()

        passed = True

        settle_min = sp - margin
        settle_max = sp + margin

        pv, sp = app.getautoagvals()
        self._log("Setting Agitation if necessary")
        app.login()
        if self.agitation:
            mode, agsp = self.agitation
            app.setag(mode, agsp)

        self._log("Setting Temp")
        app.settemp(2, 0)
        sleep(2)
        app.settemp(0, sp)
        sleep(10)
        # first loop: poll until pv within margin
        self._log("Beginning First Loop")
        while True:
            pv, actual_sp = app.getautotempvals()
            duty = app.getadvv()['MainHeatDuty(%)']

            if actual_sp != sp:
                raise TPIDBadError("SP changed during run.")

            t = _time()

            pvs.append((t, pv, duty))
            self._log("Time: %s PV: %s HD: %s" % (t, pv, duty))
            if pv > settle_min:
                break
            elif t > timeout_time:
                passed = False
                break

            _sleep(poll_interval)

        # second loop: poll for one hour
        end = _time() + settle_time

        while True:
            pv, actual_sp = app.getautotempvals()
            duty = app.getadvv()['MainHeatDuty(%)']

            if actual_sp != sp:
                raise TPIDBadError("SP changed during run.")

            t = _time()
            pvs.append((t, pv, duty))

            if pv < settle_min or pv > settle_max:
                passed = False
                # don't break here. data can be useful to keep anyway.
            elif t > end:
                break

            _sleep(poll_interval)

        self.passed = passed

    def _parse_passed(self, passed):
        """
        I should stop obsessively programming anti-dumbass features
        and just make sure not to be a dumbass.
        """
        return self._passmap[passed]

    def __repr__(self):
        obr = object.__repr__(self)
        return "%s P:%.3f I:%.3f D:%.4f Passed: %r" % (obr, self.p, self.i, self.d, self.passed)

    __str__ = __repr__

    def chartplot(self, chart):
        from officelib.xllib.xlcom import CreateDataSeries
        CreateDataSeries(chart, self.xrng, self.yrng, "P:%sI:%sD:%s" %
            (str(self.p), str(self.i), str(self.d)))

    def createplot(self, ws):
        from officelib.xllib.xlcom import CreateChart, PurgeSeriesCollection
        chart = CreateChart(ws)
        PurgeSeriesCollection(chart)
        self.chartplot(chart)
        return chart

    def _calc_xl_rngs(self, col, ws, xld):
        """
        @param col: excel column (remember 1-based indexing)
        @type col: int
        @param ws: worksheet
        @type ws: excel worksheet
        @param xld: excel data
        @type xld: list[T]
        @return: address ranges for excel data
        @rtype: (str, str)
        """

        xrng = cellRangeStr(
            (3, col),
            (2 + len(xld), col)
        )
        xrng = "=%s!%s" % (ws.Name, xrng)

        yrng = cellRangeStr(
            (3, col + 1),
            (2 + len(xld), col + 1)
        )
        yrng = "=%s!%s" % (ws.Name, yrng)

        return xrng, yrng

    def plot(self, ws, col=1):

        if self.data:
            xld = self.data
        else:
            raise TPIDBadError("Can't plot- no data!")

        cells = ws.Cells

        xrng, yrng = self._calc_xl_rngs(col, ws, xld)

        self.xrng = xrng
        self.yrng = yrng

        cells(1, col).Value = "P:"
        cells(2, col).Value = "I:"
        cells(1, col + 1).Value = str(self.p)
        cells(2, col + 1).Value = str(self.i)
        cells(1, col + 2).Value = "Passed?"
        cells(1, col + 3).Value = ("No", "Yes")[self.passed]
        cells(2, col + 2).Value = "SP:"
        cells(2, col + 3).Value = str(self.sp)
        cells(3, col + 2).Value = "D:"
        cells(3, col + 3).Value = str(self.d)

        rng = cells.Range(cells(3, col), cells(len(xld) + 2, col + 1))
        rng.Value = xld
