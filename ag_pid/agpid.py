"""

Created by: Nathan Starkweather
Created on: 09/24/2014
Created in: PyCharm Community Edition


"""
from hello.hello import HelloApp, BadError
from time import time, sleep
from officelib.xllib.xladdress import cellRangeStr
from officelib.xllib.xlcom import xlBook2
from traceback import format_exc
# from io import StringIO

__author__ = 'Nathan Starkweather'


class PIDTest():
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

    def __init__(self, p, i, sp, app_or_ipv4='192.168.1.6'):

        self.xrng = None
        self.yrng = None
        self.p = p
        self.i = i
        self.sp = sp
        self.passed = False
        self.data = None

        if type(app_or_ipv4) is HelloApp:
            self.app = app_or_ipv4
        else:
            self.app = HelloApp(app_or_ipv4)

    def run(self, settle_time=60, margin=1, timeout=120):

        app = self.app
        sp = self.sp
        pvs = []
        _time = time
        _sleep = sleep

        settle_min = sp - margin
        settle_max = sp + margin

        app.login()
        app.setconfig("Agitation", "P_Gain__(%25%2FRPM)", self.p)
        app.login()
        app.setconfig("Agitation", "I_Time_(min)", self.i)
        app.setag(0, sp)
        settle_end = _time() + settle_time

        print("Beginning Polling...")
        start = _time()
        end = _time() + timeout
        passed = True
        while True:

            pv = float(app.getagpv())
            pvs.append((_time() - start, pv))

            if not settle_min < pv < settle_max:
                t = _time()
                settle_end = t + settle_time
                if t > end:
                    passed = False
                    break

            elif _time() > settle_end:
                break

            _sleep(0.5)

        self.passed = passed
        self.data = pvs

    def _parse_passed(self, passed):
        """
        I should stop obsessively programming anti-dumbass features
        and just make sure not to be a dumbass.
        """
        return self._passmap[passed]

    def __repr__(self):
        return "P:%.2f I:%.2f Passed: %r" % (self.p, self.i, self.passed)

    __str__ = __repr__

    def _chartplot(self, chart):
        from officelib.xllib.xlcom import CreateDataSeries
        CreateDataSeries(chart, self.xrng, self.yrng, repr(self))

    def _createplot(self, ws):
        from officelib.xllib.xlcom import CreateChart, PurgeSeriesCollection
        chart = CreateChart(ws)
        PurgeSeriesCollection(chart)
        self._chartplot(chart)
        return chart

    def _calc_xl_rngs(self, col, ws, xld):
        # xrng and yrng not used in this function,
        # but we have the info here to calculate them
        # and preserve state
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

    def plot(self, wb_name, ws_num=1, col=1):

        if self.data:
            xld = self.data
        else:
            raise BadError("Can't plot- no data!")

        xl, wb = xlBook2(wb_name)
        ws = wb.Worksheets(ws_num)
        cells = ws.Cells

        xrng, yrng = self._calc_xl_rngs(col, ws, xld)

        self.xrng = xrng
        self.yrng = yrng

        cells(1, col).Value = "P:"
        cells(2, col).Value = "I:"
        cells(1, col + 1).Value = str(self.p)
        cells(2, col + 1).Value = str(self.i)
        cells(1, col + 2).Value = "Passed?"
        cells(2, col + 2).Value = ("No", "Yes")[self.passed]

        rng = cells.Range(cells(3, col), cells(len(xld) + 2, col + 1))
        rng.Value = xld


class PIDRunner():
    """ runner for many PID tests

    @type tests: list[PIDTest]
    """

    def __init__(self, pgains=(), itimes=(), sps=(), othercombos=(),
                 ws_name=None, app_or_ipv4='192.168.1.6'):
        """

        Pass values for ALL of pgains/itimes/sps or NONE. Otherwise,
        error.

        @param pgains: pgains to do all combinations of w/ itimes
        @type pgains: collections.Iterable[int|float]

        @param itimes: itimes to do all combinations of w/ pgains
        @type itimes: collections.Iterable[int|float]

        @param sps: set points to do all combinations of
        @type sps: collections.Iterable[int|float]

        @param othercombos: all other combinations of (p, i, sp) to try
        @type othercombos: collections.Iterable[(int|float, int|float, int|float)]

        @param ws_name: ws to plot in
        @type ws_name: str


        """

        if bool(pgains) != bool(itimes) != bool(sps):
            raise BadError("Must pass in ALL or NONE of pgains, itimes, sps")

        self.app_or_ipv4 = app_or_ipv4

        self.combos = []
        for p in pgains:
            for i in itimes:
                for s in sps:
                    self.combos.append((p, i, s))

        for combo in othercombos:
            self.combos.append(combo)

        self.wb_name = ws_name
        self.logbuf = []
        self.tests = []

    def runall(self):

        q = self.app_or_ipv4
        if type(q) is HelloApp:
            app = q
        else:
            app = HelloApp(q)

        # don't use enumerate- don't increment counter
        # for failed tests
        for p, i, sp in self.combos:
            self.log("Running test P:%.2f I:%.2f SP: %.2f" % (p, i, sp))
            t = PIDTest(p, i, sp, app_or_ipv4=app)
            try:
                t.run()
            except (KeyboardInterrupt, SystemExit):
                self.log_err("Got critical interrupt")
            except Exception:
                self.log_err("Error in PIDTest.run():")
                continue
            else:
                self.log("Successful test")
                self.tests.append(t)

    def plotall(self):
        i = 1
        self.log("Plotting All tests in ", self.wb_name or "New Workbook")
        for t in self.tests:
            self.log("\tPlotting:", repr(t))
            try:
                t.plot(self.wb_name, 1, i)
                i += 3
            except:
                self.log_err("Error plotting")

    def log_err(self, *msg):
        self.log(*msg)
        self.log(format_exc())

    def log(self, *args):
        """ Log stuff. print to console, save a copy to
        internal log buffer. """
        line = ' '.join(args)
        self.logbuf.append(line)
        print(line)

    def _get_log_fname(self):
        from os.path import exists
        from datetime import datetime

        tmplt = "./agpid_log %s%%s.log" % datetime.now().strftime("%y%m%d%H%M%S")
        fpth = tmplt % ''
        n = 1
        while exists(fpth):
            fpth = tmplt % (' ' + str(n))
            n += 1
        return fpth, 'w'

    def commit_log(self):
        fpth, mode = self._get_log_fname()
        with open(fpth, mode) as f:
            f.writelines(self.logbuf)
        self.logbuf.clear()

    def __del__(self):
        if self.logbuf:
            self.commit_log()
