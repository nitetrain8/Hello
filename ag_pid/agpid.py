"""

Created by: Nathan Starkweather
Created on: 09/24/2014
Created in: PyCharm Community Edition


"""
from os.path import exists as path_exists, split as path_split
from os import makedirs
from hello.hello import HelloApp, BadError, AuthError
from time import time, sleep
from officelib.xllib.xladdress import cellRangeStr
from officelib.xllib.xlcom import xlBook2
from traceback import format_exc
from datetime import datetime
from io import StringIO

__author__ = 'Nathan Starkweather'


_getnow = datetime.now


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
        app.setconfig("Agitation", "P_Gain__(%/RPM)", self.p)
        app.login()
        app.setconfig("Agitation", "I_Time_(min)", self.i)

        app.login()
        app.setag(2, 0)

        _sleep(30)

        app.setag(0, sp)
        settle_end = _time() + settle_time

        print("Beginning Polling...")
        start = _time()
        end = start + timeout
        passed = True
        while True:

            pv = app.getagpv()
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

    def chartplot(self, chart):
        from officelib.xllib.xlcom import CreateDataSeries
        CreateDataSeries(chart, self.xrng, self.yrng, repr(self))

    def createplot(self, ws):
        from officelib.xllib.xlcom import CreateChart, PurgeSeriesCollection
        chart = CreateChart(ws)
        PurgeSeriesCollection(chart)
        self.chartplot(chart)
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

    def plot(self, ws, col=1):

        if self.data:
            xld = self.data
        else:
            raise BadError("Can't plot- no data!")

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
        cells(1, col + 3).Value = "SP:"
        cells(2, col + 3).Value = str(self.sp)

        rng = cells.Range(cells(3, col), cells(len(xld) + 2, col + 1))
        rng.Value = xld


class PIDRunner():
    """ runner for many PID tests

    @type _tests: list[PIDTest]
    """

    _docroot = "C:/Users/Public/Documents/PBSSS/Agitation/Mag Wheel PID/"

    def __init__(self, pgains=(), itimes=(), sps=(), othercombos=(),
                 wb_name=None, app_or_ipv4='192.168.1.6'):
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

        @param wb_name: ws to plot in
        @type wb_name: str


        """

        if bool(pgains) != bool(itimes) != bool(sps):
            raise BadError("Must pass in ALL or NONE of pgains, itimes, sps")

        self._app_or_ipv4 = app_or_ipv4

        self._combos = []
        for p in pgains:
            for i in itimes:
                for s in sps:
                    self._combos.append((p, i, s))

        for combo in othercombos:
            self._combos.append(combo)

        self._wb_name = wb_name or "AgPIDTest %s" % datetime.now().strftime("%y%m%d%H%M")
        self._full_xl_name = self._docroot + self._wb_name
        self._logbuf = StringIO()
        self._tests = []
        self._closed = False

        self._xl = None
        self._wb = None
        self._ws = None
        self._chart = None

    def doall(self):
        self.runall()
        self.plotall()
        self.chartbypid()

    def runall(self):

        q = self._app_or_ipv4
        if type(q) is HelloApp:
            app = q
        else:
            app = HelloApp(q)

        self._init_settings(app)

        for p, i, sp in self._combos:
            self._log("Running test P:%.2f I:%.2f SP: %.2f" % (p, i, sp))
            t = PIDTest(p, i, sp, app_or_ipv4=app)
            try:
                t.run()
            except (KeyboardInterrupt, SystemExit):
                self._log_err("Got critical interrupt")
                raise
            except Exception:
                self._log_err("Error in PIDTest.run():")
                continue
            else:
                self._log("Successful test")
                self._tests.append(t)

    def _init_xl(self):
        if path_exists(self._full_xl_name):
            self._log("Opening existing workbook")
            xl, wb = xlBook2(self._full_xl_name, True, False)
        else:
            xl, wb = xlBook2(None, True, False)
            wb.SaveAs(self._full_xl_name, AddToMru=True)
        ws = self._wb.Worksheets(1)

        return xl, wb, ws

    def chartall(self):

        chart = self._init_chart()

        for t in self._tests:
            self._log("Plotting data:", repr(t), end=' ')
            try:
                t.chartplot(chart)
            except:
                self._log_err("Error plotting")
            else:
                self._log("Success!")

    def chartbypid(self, ifpassed=False):

        groups = {}
        for t in self._tests:

            if ifpassed and not t.passed:
               continue

            key = (t.p, t.i)
            if key not in groups:
                groups[key] = self._init_chart()
            t.chartplot(groups[key])

        for key in groups:
            p, i = key
            name = "P:%sI:%s" % (str(p), str(i))
            groups[key].Location(1, name)

    def plotall(self):

        self._log("Copying test data to ", self._wb_name or "New Workbook")

        d = path_split(self._full_xl_name)[0]

        try:
            makedirs(d)
        except FileExistsError:
            pass

        self._xl, self._wb, self._ws = self._init_xl()

        ntests = len(self._tests)
        col = 1

        for n, t in enumerate(self._tests, 1):
            self._log("\tCopying data for test %d of %d" % (n, ntests), repr(t), end=' ')
            try:
                t.plot(self._ws, col)
                col += 5
            except:
                self._log_err("Error copying data")
            else:
                self._log("Success!")

        self._log("Done copying data for %d tests." % ntests)

    def _log_err(self, *msg, **pkw):
        self._log(*msg, **pkw)
        self._log(format_exc())

    def _log(self, *args, **pkw):
        """ Log stuff. print to console, save a copy to
        internal log buffer. """
        line = ' '.join(args)
        now = _getnow().strftime("%m/%d/%Y %H:%M:%S")
        print(now, line, file=self._logbuf, **pkw)
        print(now, line)

    def _get_log_name(self):

        tmplt = self._docroot + "repllog/agpid_log %s%%s.log" % _getnow().strftime("%y%m%d%H%M%S")
        fpth = tmplt % ''
        n = 1
        while path_exists(fpth):
            fpth = tmplt % (' ' + str(n))
            n += 1
        return fpth, 'w'

    def _commit_log(self):
        fpth, mode = self._get_log_name()

        # just in case the log is really big, avoid derping
        # the whole thing into memory at once.
        with open(fpth, mode) as f:
            self._logbuf.seek(0, 0)
            for line in self._logbuf:
                print(line, file=f)
        self._logbuf = StringIO()

    def close(self):
        if self._closed:
            return
        self._closed = True

        if self._logbuf:
            self._commit_log()

        if self._xl is not None:
            self._xl.Visible = True
            self._xl = None

        self._wb = None
        self._ws = None
        self._chart = None

        tmplt = self._docroot + "agpid_bkup cache %s%%s.pickle" % datetime.now().strftime("%y%m%d%H%M%S")
        fpth = tmplt % ''
        n = 1
        while path_exists(fpth):
            fpth = tmplt % (' ' + str(n))
            n += 1

        from pysrc.snippets.safe_write import safe_pickle
        safe_pickle(self, fpth)

    def __del__(self):
        self.close()

    # def _repr(self):
    #     l1 = super().__repr__()

    def _init_settings(self, app):
        settings = (
            ("Agitation", "Minimum (RPM)", 3),
            ("Agitation", "Power Auto Max (%)", 100),
            ("Agitation", "Power Auto Min (%)", 3.9),
            ("Agitation", "Auto Max Startup (%)", 7),
            ("Agitation", "Samples To Average", 3),
            ("Agitation", "Min Mag Interval (s)", 0.1),
            ("Agitation", "Max Change Rate (%/s)", 100),
            ("Agitation", "PWM Period (us)", 1000),
            ("Agitation", "PWM OnTime (us)", 1000)
        )

        self._log("Initializing Settings")
        for grp, setting, val in settings:
            self._log("Setting %s %s to %s" % (grp, setting, str(val)))
            app.login()
            app.setconfig(grp, setting, val)
        self._log("Initialization Successful")

    def _init_chart(self):

        from officelib.xllib.xlcom import CreateChart, PurgeSeriesCollection
        self._log("Initializing chart")
        chart = CreateChart(self._ws)
        PurgeSeriesCollection(chart)
        return chart

    def chartbyfilter(self, **kw):
        items = tuple(kw.items())

        self._log("Charting by filter:", kw)

        def fltr(ob):
            for k, v in items:
                if getattr(ob, k) != v:
                    return False
            return True

        matches = tuple(filter(fltr, self._tests))

        self._log("Plotting %d tests in new chart" % len(matches))

        chart = self._init_chart()
        for m in matches:
            m.chartplot(chart)

        chart_name = ''.join("%s=%s" % it for it in items)
        chart.Location(1, chart_name)
