"""

Created by: Nathan Starkweather
Created on: 09/24/2014
Created in: PyCharm Community Edition


"""
from collections import OrderedDict
from os.path import exists as path_exists, split as path_split, splitext
from os import makedirs
import os
from time import time, sleep
from datetime import datetime
from io import StringIO
from pysrc.snippets.unique import unique_name
from pysrc.snippets.safe_write import safe_pickle

from hello.hello3 import HelloApp, BadError, open_hello, OFF, AUTO, MAN
from officelib.xllib.xladdress import cellRangeStr
from officelib.xllib.xlcom import xlBook2, FormatChart
from pysrc.logger import Logger, BuiltinLogger
from officelib.xllib.xlcom import HiddenXl
from officelib.xllib.xlcom import CreateChart, PurgeSeriesCollection, CreateDataSeries


__author__ = 'Nathan Starkweather'

# --------------------------------------------------
# Util
# --------------------------------------------------
_now = datetime.now


def _flattenify_inner(ob, into):
    for o in ob:
        if isinstance(o, (list, tuple)):
            _flattenify_inner(o, into)
        else:
            into.append(o)
def _flattenify(ob):
    rv = []
    _flattenify_inner(ob, rv)
    return rv

def _flattened_data(data):
    return [_flattenify(d) for d in data]

def _xl_rng_for_data(col, row_os, ws, xld):
    xrng = cellRangeStr(
        (row_os, col),
        (row_os - 1 + len(xld), col)
    )
    xrng = "=%s!%s" % (ws.Name, xrng)

    yrng = cellRangeStr(
        (row_os, col + 1),
        (row_os - 1 + len(xld), col + 1)
    )
    yrng = "=%s!%s" % (ws.Name, yrng)
    return xrng, yrng

_minute = 60
_hour = _minute * 60

# class AgPIDInfo():
#     """ PID configuration """
#     def __init__(self, p, i, d):
#         self.p = p
#         self.i = i
#         self.d = d

#     def apply_settings(self, app):
#         app.setconfig("Agitation", "P_Gain_(%/RPM)", self.p)
#         app.setconfig("Agitation", "I_Time_(min)", self.i)
#         app.setconfig("Agitation", "D Time (min)", self.d)


class PIDError(Exception):
    pass

class TestFailure(PIDError):
    pass


class TestInfo():
    """ Test Info.
    The plan is to use this as an easy way to reference
    and adjust all the configuration constants and parameters
    spread out across the Controller, PIDTest, and Mixin
    classes. 
    """
    def __init__(self):
        self._default = object()
        self.sp = self._default
        self.start_pv = self._default
        self.settle_time = self._default
        self.timeout = self._default
        self.error_band = self._default
        self.mintime = self._default
        self.ctrl_name = self._default

    def _decide(self, old, new):
        if new is self._default:
            return old
        return new

    def apply(self, pidtest):
        pidtest.sp = self._decide(pidtest.sp, self.sp)
        pidtest.start_pv = self._decide(pidtest.start_pv, self.start_pv)
        pidtest.settle_time = self._decide(pidtest.settle_time, self.settle_time)
        pidtest.timeout = self._decide(pidtest.timeout, self.timeout)
        pidtest.error_band = self._decide(pidtest.error_band, self.error_band)
        pidtest.mintime = self._decide(pidtest.mintime, self.mintime)
        pidtest.ctrl.name = self._decide(pidtest.ctrl.name, self.ctrl_name)


def _interruptable_sleep(n):
    # interruptible sleep routine
    start = time()
    while time() - start < n:
        sleep(1)

import abc
class Controller(abc.ABC):
    group = ""
    name = "Controller"
    pvunit = "Units"
    manunit = "Units"
    def __init__(self, app, logger):
        self.app = app
        self.gpmv = app.gpmv
        self.logger = logger
    def set(self, mode, sp1=0, sp2=0):
        self.app.login()
        self.app.set_mode(self.group, mode, sp)
    def auto(self, sp):
        self.logger.info("Setting %s to %d%s", self.name, sp, self.pvunit)
        self.set(AUTO, sp)
    def man(self, op, op2=None):
        self.logger.info("Setting %s to %d%s", self.name, op, self.manunit)
        self.set(MAN, sp)
    def off(self, sp=0):
        self.logger.info("Setting %s to Off", self.name)
        self.set(OFF)
    def getpv(self):
        return self.app.gpmv()[self.group]['pv']
    def getpvop(self):
        group = self.app.gpmv()[self.group]
        pv = group['pv']
        op = group['output']
        return pv, op 


class AgController(Controller):
    name = "Agitation"
    group = "agitation"
    pvunit = "RPM"
    manunit = "%"


class TempController(Controller):
    name = "Temperature"
    group = "temperature"
    pvunit = "C"
    manunit = "%"


class PIDTest():
    DATA_POLL_INTERVAL = 0.5
    SHORT_NAME = "Default"
    ControllerClass = Controller
    CURRENT_PV = object()

    # test parameters
    pretest_stabilize = 30
    pretest_stabilize_timeout = 60
    pretest_stabilize_margin = 0.5
    settle_time = 120
    timeout = 180
    error_band = 1
    mintime = 180

    def __init__(self, p, i, d, start_pv, sp, app_or_ipv4=None, logger=None, name=None, metadata=None):
        """
        @param p: pgain
        @param i: itime
        @param d: dtime
        @param sp: set point
        @param app_or_ipv4: HelloApp object, or IPV4 to pass to HelloApp constructor
        """
        self.xrng = None
        self.yrng = None
        self.namerng = None
        self.p = p
        self.i = i
        self.d = d
        self.sp = sp
        self.passed = False
        self.data = []
        self.logger = logger or BuiltinLogger(self.__class__.__name__)
        self.metadata = metadata or {}
        if app_or_ipv4 is None:
            raise ValueError("Must provide app or ipv4")
        self.app = open_hello(app_or_ipv4)
        self.ctrl = self.ControllerClass(self.app, self.logger)

        if start_pv is self.CURRENT_PV:
            start_pv = self.ctrl.getpv()
        self.start_pv = start_pv
        self.name = name or self.defaultname()

    def get_chart_key(self):
        return self.p, self.i, self.d, self.SHORT_NAME

    def defaultname(self):
        return "%s-%s-%s-%s-%s" % (self.__class__.__name__, self.p, self.i, self.d, self.sp)

    def chartplot(self, chart):
        CreateDataSeries(chart, self.xrng, self.yrng, self.namerng)

    def sorted_metadata(self):
        """ Sort metadata into two item tuples for 
        addition to header data prior to pasting into
        excel. 
        Can also be used to filter out unwanted metadata
        if necessary. 
        """
        return sorted(self.metadata.items())

    def make_header_data(self):
        data = [
            [self.name, "", "", ""],
            ["P:", str(self.p), "Passed?", ("No", "Yes")[self.passed]],
            ["I:", str(self.i), "SP:", str(self.sp)],
            ["D:", str(self.d), "", ""]
        ]

        # This algorithm adds each (key, value) pair of 
        # metadata into rows two columns i.e.
        #  0       1        2       3
        # key1   value1   key2    value2
        # key3   value3   key4    value4
        # 
        # Data is added in order as returned by 
        # self.sorted_metadata()
        idx = 1
        for k, v in self.sorted_metadata():
            if idx == 0:
                data.append(["", "", "", ""])
                a, b = 0, 1
            else:
                a, b = 2, 3
            data[-1][a] = str(k) + ":"
            data[-1][b] = str(v)
            idx = 1 - idx  # flip flop 0 -> 1 -> 0
        return data

    def plot(self, ws, col=1):

        if self.data:
            xld = _flattened_data(self.data)
        else:
            raise BadError("Can't plot- no data!")

        cells = ws.Cells
        self.namerng = "='%s'!%s" % (ws.Name, cells(1, col).Address)

        header = self.make_header_data()
        header_range = cells.Range(cells(1, col), cells(len(header), col+len(header[0])-1))
        header_range.Value = header
        next_row = len(header) + 1
        cells(next_row, col).Value = "T(sec)"
        cells(next_row, col+1).Value = "PV (%s)" % self.ctrl.pvunit
        cells(next_row, col+2).Value = "Output (%s)" % self.ctrl.manunit

        tl_data = cells(next_row + 1, col)
        br_data = tl_data.Offset(len(xld), len(xld[0]))
        rng = cells.Range(tl_data, br_data)
        rng.Value = xld
        cols_used = max(5, len(xld[0]) + 1)  # 4 metadata + 1 space, or # of data columns + 1 space

        xrng, yrng = _xl_rng_for_data(col, next_row+1, ws, xld)
        self.xrng = xrng
        self.yrng = yrng
        
        return cols_used

    def run(self):
        self.logger.info("Beginning test run for %s", self.defaultname())

        # setup & begin test
        self.setup_settings()
        self.setup_test()
        self.data = []
        settle_min, settle_max = self.get_settle_margins()
        start = time()
        mintime_end = start + self.mintime
        end = start + self.timeout    
        self.start_test()
   
        # execute test
        self.passed = self.wait_for_settle(self.data, start, end, settle_min, 
                            settle_max, self.settle_time, self.sp)
        self.wait_for_min_time(self.data, start, mintime_end)
        self.logger.info("Finished Test")

    def setup_settings(self):
        pass

    def setup_test(self):
        pass

    def verify_setup_stable(self):
        success = self.wait_for_settle([], time(), time() + self.pretest_stabilize_timeout,
                             self.start_pv - self.pretest_stabilize_margin, 
                             self.start_pv + self.pretest_stabilize_margin, 
                             self.pretest_stabilize, self.start_pv)
        # if abs(self.ctrl.getpv() - self.start_pv) > margin:
        if not success:
            raise ValueError("Failed to stabilize at %d %s", self.start_pv, self.ctrl.name)

    def get_settle_margins(self):
        settle_min = self.sp - self.error_band
        settle_max = self.sp + self.error_band
        return settle_min, settle_max

    def start_test(self):
        self.logger.info("Starting Test")
        self.ctrl.auto(self.sp)

    def wait_for_settle(self, data, start, end, settle_min, 
                            settle_max, settle_time, sp="<n/a>"):

        self.logger.info("Waiting for PV to settle")
        settle_end = start + settle_time
        passed = True
        next_update = start
        while True:
            pv, op = self.ctrl.getpvop()
            t = time()
            data.append((t - start, pv, op))
            if not (settle_min < pv < settle_max):
                settle_end = t + settle_time
                if t > end:
                    passed = False
                    break
            elif t > settle_end:
                break
            if t > next_update:
                self.logger.info("Update: PV: %.2f SP: %.2f Settle Remaining: %d Timeout: %d", pv, sp, settle_end - t, max(end - t, 0))
                next_update += 60
            sleep(self.DATA_POLL_INTERVAL)
        return passed

    def wait_for_min_time(self, data, start, mintime_end):
        t = time()
        if t > mintime_end:
            return
        self.logger.info("Waiting %d seconds to finish test", mintime_end - t)
        next_update = t + 60
        while t < mintime_end:
            pv, op = self.ctrl.getpvop()
            t = time()
            data.append((t - start, pv, op))
            sleep(self.DATA_POLL_INTERVAL)
            if t > next_update:
                next_update += 60
                self.logger.info("Update: Waiting %d seconds to finish test.", mintime_end - t)


    def __repr__(self):
        return "P:%.3f I:%.3f D:%.4f SP:%d" % (self.p, self.i, self.d, self.sp)
    __str__ = __repr__

# =====================================
# Mixins implement behavior for the following 
# types of tests:
# * Off to Auto
# * Auto to Auto
# * Man to Auto
# * Man to Man
# =====================================

class OffToAutoMixin():
    off_sleep = 30
    SHORT_NAME = "O2A"
    def setup_test(self):
        self.logger.info("Setting %s to OFF and waiting %d seconds", self.ctrl.name, self.off_sleep)
        self.ctrl.off()
        _interruptable_sleep(self.off_sleep)

    def defaultname(self):
        return "OffToAuto SP:%.1f" % self.sp


class AutoToAutoMixin():
    SHORT_NAME = "A2A"
    def setup_test(self):
        self.logger.info("Setting %s to AUTO %d %s and waiting until stable for %d seconds (%d second timeout)", 
                            self.ctrl.name, self.start_pv, self.ctrl.pvunit, self.pretest_stabilize, self.pretest_stabilize_timeout)
        self.ctrl.auto(self.start_pv)
        self.verify_setup_stable()

    def defaultname(self):
        return "AutoToAuto Start:%.1f SP:%.1f" % (self.start_pv, self.sp)


class ManToAutoMixin():
    SHORT_NAME = "M2A"

    def setup_test(self):
        self.logger.info("Setting %s to AUTO %d %s and waiting until stable for %d seconds (%d second timeout)", 
                                    self.ctrl.name, self.start_pv, self.ctrl.pvunit, self.pretest_stabilize, self.pretest_stabilize_timeout)
        self.ctrl.off()
        _interruptable_sleep(5)
        self.ctrl.auto(self.start_pv)
        self.verify_setup_stable()
        op, pv = self.ctrl.getpvop()
        self.logger.info("Setting %s to MAN at output (%.2f) for PV (%.1f %s)", 
                            self.ctrl.name, op, pv, self.ctrl.pvunit)
        self.ctrl.man(op)
        # Allow anyone observing bioreactor to see 
        # the change take effect. 
        _interruptable_sleep(5)

    def defaultname(self):
        return "ManToAuto Start:%.1f SP:%.1f" % (self.start_pv, self.sp)


class ManToManMixin():
    SHORT_NAME = "M2M"

    def setup_test(self):
        self.ctrl.off()
        _interruptable_sleep(5)
        self.ctrl.auto(self.start_pv)
        _interruptable_sleep(30)
        if abs(self.ctrl.getpv() - self.start_pv) > 1:
            raise ValueError("Failed to stabilize %s during setup_test", self.ctrl.name)
        _, op = self.ctrl.getpvop
        self.logger.info("Setting %s to MAN at output (%.2f) for PV (%d %s)" % (self.ctrl.name, op, self.start_pv, self.ctrl.pvunit))
        self.ctrl.man(op)
        _interruptable_sleep(5)  # ensure change is visible to operator on bioreactor

    def start_test(self):
        pv, op = self.ctrl.getpvop()
        ratio = op / pv
        man = ratio * self.sp  # assume linear relationship
        self.logger.info("Setting %s to %.1f%%", self.ctrl.name, man)
        self.ctrl.man(man)

    def defaultname(self):
        return "ManToMan Start:%.1f SP:%.1f" % (self.start_pv, self.sp)


# ===================================================
# Controller specific setup
# ===================================================


class AgPIDTest(PIDTest):
    ControllerClass = AgController

    # test parameters
    settle_time = 120
    timeout = 180
    error_band = 1
    mintime = 180

    def setup_settings(self):
        self.logger.info("Setting PID Settings")
        self.app.login()
        self.app.setconfig("Agitation", "P_Gain_(%/RPM)", self.p)
        self.app.setconfig("Agitation", "I_Time_(min)", self.i)
        self.app.setconfig("Agitation", "D_Time_(min)", self.d)


class TempPIDTest(PIDTest):
    ControllerClass = TempController
    def setup_settings(self):
        self.logger.info("Setting PID Settings")
        self.app.login()
        self.app.setconfig("Temperature", "P_Gain_(%/C)", self.p)
        self.app.setconfig("Temperature", "I_Time_(min)", self.i)
        self.app.setconfig("Temperature", "D_Time_(min)", self.d)



# ===================================================
# Concrete classes
# ===================================================

# Agitation
class AgOffToAutoTest(OffToAutoMixin, AgPIDTest): pass
class AgAutoToAutoTest(AutoToAutoMixin, AgPIDTest): pass
class AgManToAutoTest(ManToAutoMixin, AgPIDTest): pass
class AgManToManTest(ManToManMixin, AgPIDTest): pass

# Temperature
class TempOffToAutoTest(TempPIDTest):
    SHORT_NAME = "O2A"
    pretest_stabilize_timeout   = 60 * _minute
    pretest_stabilize_margin    = 0.2
    settle_time                 = 60 * _minute
    timeout                     = 3 * _hour
    error_band                  = 0.2
    mintime                     = 3 * _hour
    wait_for_cooling            = True
    agitation_sp                = 12

    def setup_test(self):
        self.ctrl.off()
        self.app.setag(AUTO, self.agitation_sp)
        if self.wait_for_cooling:
            end = time() + self.pretest_stabilize_timeout
            while time() < end and self.ctrl.getpv() > self.start_pv:
                _interruptable_sleep(10)
            if time() > end:
                raise TestFailure("Failed to cool to starting pv")
        # wait a bit before starting the test
        _interruptable_sleep(10)

    def defaultname(self):
        return "OffToAuto Start:%.1f SP:%.1f" % (self.start_pv, self.sp)


class TempAutoToAutoTest(AutoToAutoMixin, TempPIDTest):
    # test parameters
    pretest_stabilize           = 30 * _minute
    pretest_stabilize_timeout   = 60 * _minute
    pretest_stabilize_margin    = 0.2
    settle_time                 = 30 * _minute
    timeout                     = 3 * _hour
    error_band                  = 0.2
    mintime                     = 1 * _hour
    agitation_sp                = 12
    
    def setup_test(self):
        self.app.setag(AUTO, self.agitation_sp)
        super().setup_test()


class TempManToAutoTest(ManToAutoMixin, TempPIDTest): 
    pretest_stabilize           = 30 * _minute
    pretest_stabilize_timeout   = 3 * _hour
    pretest_stabilize_margin    = 0.1
    settle_time                 = 1 * _hour
    timeout                     = 3 * _hour
    error_band                  = 0.2
    mintime                     = 2 * _hour
    agitation_sp                = 12

    def setup_test(self):
        self.app.setag(AUTO, self.agitation_sp)
        self.logger.info("Setting %s to AUTO %d %s and waiting until stable for %d seconds (%d second timeout)", 
                                    self.ctrl.name, self.start_pv, self.ctrl.pvunit, self.pretest_stabilize, self.pretest_stabilize_timeout)
        self.ctrl.auto(self.start_pv)
        self.verify_setup_stable()
        pv, op = self.ctrl.getpvop()
        self.logger.info("Setting %s to MAN at output (%.2f) for PV (%.1f %s)", 
                            self.ctrl.name, op, pv, self.ctrl.pvunit)
        self.ctrl.man(op)
        # Allow anyone observing bioreactor to see 
        # the change take effect. 
        _interruptable_sleep(5)

class TempManToManTest(ManToManMixin, TempPIDTest):
    agitation_sp = 12
    def setup_test(self):
        self.app.setag(AUTO, self.agitation_sp)
        super().setup_test()


class PIDRunner():
    """ Runner for many PID tests """

    _docroot = "C:\\Users\\Nathan\\Documents\\PBS\\PID Tuning\\"

    def __init__(self, tests=(), wb_name=None, ignore_keyboardinterrupt=False):

        self.logger = BuiltinLogger("PID Test", path=self._docroot)
        self.ignore_keyboardinterrupt = ignore_keyboardinterrupt
        self._tests = []
        for t in tests:
            self.add_test(t)
    
        # Misc
        self._wb_name = None
        self._full_xl_name = None
        self._xl = None
        self._wb = None
        self._ws = None
        self._chart = None
        self._chartmap = None

        wb_name = wb_name or "PIDTest %s.xlsx" % datetime.now().strftime("%m-%d-%y %H-%M")
        self.set_wb_name(wb_name)

    def add_test(self, test):
        self._tests.append(test)

    def set_wb_name(self, name):
        self._wb_name = name
        self._full_xl_name = self._docroot + name

    def doall(self):
        """
        Common functions chained together.
        """
        self.runall()
        self.plotall()
        with HiddenXl(self._xl):
            self.chartbypid()
        self._wb.Save()

    def runall(self):
        """
        Run all tests in container. If Error or interrupt occurs,
        test is *not* added to the list of completed tests.
        """
        ntests = len(self._tests)
        ki = 0

        for n, t in enumerate(self._tests, 1):
            self.logger.info("Running test %d of %d: %s", n, ntests, repr(t))
            try:
                t.run()
            except KeyboardInterrupt:
                self.logger.error("Got keyboard interrupt, skipping test.")
                if not self.ignore_keyboardinterrupt:
                    ki += 1
                    if ki >= 2:
                        rsp = input("Got more keyboard interrupts. Type 'quit' to quit.")
                        if rsp.lower() == 'quit':
                            raise
                else:
                    raise
            except SystemExit:
                self.logger.error("Got system interrupt, aborting run.", exc_info=1)
                raise
            except Exception:
                self.logger.error("Error in PIDTest.run():", exc_info=1)
            else:
                self.logger.info("Successful test")

    def _init_xl(self):
        """
        Initialize the excel instance used by other functions
        """
        if self._xl is None:
            self._full_xl_name = unique_name(self._full_xl_name)
            self._xl, self._wb = xlBook2(None, True, False)
            self._wb.SaveAs(self._full_xl_name, AddToMru=True)
            self._ws = self._wb.Worksheets(1)
        

    def chartbypid(self, ifpassed=False):
        """
        @param ifpassed: Only plot tests that passed
        @type ifpassed: Bool

        Group all tests with the same p,i,d settings into one chart. Ie,
        all setpoints for a given set of settings in one chart.
        """
        groups = OrderedDict()
        for t in self._tests:

            if ifpassed and not t.passed:
                continue

            key = t.get_chart_key()
            if key not in groups:
                groups[key] = self._new_chart()
            t.chartplot(groups[key])

        # loop again and format + move charts to new sheets
        for key, chart in groups.items():
            p, i, d, other = key
            name = "P%sI%sD%s %s" % (str(p), str(i), str(d), other)
            name2 = "P: %s I: %s D:%s %s" % (p, i, d, other)
            title = "PID Test: " + name2
            self.logger.info("Formatting Chart: %s", name2)
            try:
                FormatChart(chart, ChartTitle=title, xAxisTitle="Time (s)", yAxisTitle="PV", Legend=True)
                chart.Location(1, name)
                axes = chart.Axes(AxisGroup=2)  # xlPrimary
                axes(1).HasMajorGridlines = True
                axes(2).HasMajorGridlines = True
            except Exception:
                self.logger.error("Error Formatting chart", exc_info=1)

        self._chartmap = groups

    def plotall(self):
        """
        Despite the name, this simply copies data into the
        excel sheet, according to PIDTest.plot() method.
        """
        d = path_split(self._full_xl_name)[0]
        makedirs(d, exist_ok=True)
        self._init_xl()
        ntests = len(self._tests)
        col = 1
        with HiddenXl(self._xl):
            self.logger.info("Copying test data to " + self._wb_name or "New Workbook")
            for n, t in enumerate(self._tests, 1):
                self.logger.info("Copying data for test %d of %d", n, ntests)
                try:
                    col += t.plot(self._ws, col)
                except Exception:
                    self.logger.error("Error copying data for test #%d", n, exc_info=1)
            self.logger.info("Done copying data for %d tests.", ntests)

    def backup(self):
        """
        Pickle stuff. 
        """
        file = "agpid_bkup cache %s.pkl" % datetime.now().strftime("%y%m%d%H%M%S")
        fpth = os.path.join(self._docroot, file)
        fpth = unique_name(fpth)
        data = []
        for t in self._tests:
            d = t.__dict__.copy()
            del d['app']
            del d['logger']
            data.append(d)
        try:
            safe_pickle(data, fpth)
        except Exception:
            self.logger.error("Couldn't pickle data", exc_info=1)

    def _new_chart(self):
        self.logger.info("Initializing chart")
        chart = CreateChart(self._ws)
        PurgeSeriesCollection(chart)
        return chart


class SimplePIDRunner(PIDRunner):
    def __init__(self, p=(), i=(), d=(), sp=(), othercombos=(), tests=(), wb_name=None, app_or_ipv4='192.168.1.6'):
        from numbers import Number
        def to_iter(ob, ifempty=()):
            if not ob:
                return ifempty
            elif isinstance(ob, (int, float, str, Number)):
                return ob,
            else:
                return ob
        ps = to_iter(p)
        its = to_iter(i)
        ds = to_iter(d)
        sps = to_iter(sp)
        app = open_hello(app_or_ipv4)
        tests = list(tests)
        tests.extend(AgOffToAutoTest(p, i, d,sp,app) for p in ps for i in its for d in ds for s in sps)
        tests.extend(AgOffToAutoTest(p, i, d, sp,app) for p, i, d, sp in othercombos)
        super().__init__(tests=tests, wb_name=wb_name, app_or_ipv4=app_or_ipv4)