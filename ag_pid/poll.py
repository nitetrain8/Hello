"""

Created by: Nathan Starkweather
Created on: 09/26/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from hello.logger import PLogger
from hello.hello import HelloApp
from time import time, sleep
from datetime import datetime
from officelib.xllib.xladdress import cellRangeStr

_now = datetime.now


class PollError(Exception):
    pass


class _Poller(PLogger):

    def __init__(self, name, app_or_ipv4):
        PLogger.__init__(self, name)
        self._app_or_ipv4 = app_or_ipv4

    def _init_app(self):

        if self._app is not None:
            return

        if type(self._app_or_ipv4) is HelloApp:
            self._log("Using existing HelloApp object")
            self._app = self._app_or_ipv4
        else:
            self._log("Initializing new HelloApp object")
            self._app = HelloApp(self._app_or_ipv4)

    @classmethod
    def copy(cls, self):
        new = cls(self._sps, self._ramp_time, self._poll_time, self._app_or_ipv4)
        new._power_curve_results = self._results.copy()
        return new

    def _init_xl(self, name=None):
        from officelib.xllib.xlcom import xlObjs

        date = _now().strftime(self._savedateformat)
        name = ''.join((
            name or "Poll Results",
            " ",
            date,
            ".xlsx"
        ))
        dir = "C:\\Users\\Public\\Documents\\PBSSS\\Agitation\\Mag Wheel PID\\"
        fpth = dir + name
        xl, wb, ws, cells = xlObjs()
        wb.SaveAs(fpth, AddToMru=True)
        return xl, wb, ws, cells


class Poller(_Poller):
    """
    @type _app: HelloApp
    """

    def __init__(self, sps=(), ramp_time=40,
                 poll_time=360, app_or_ipv4='192.168.1.6'):
        super().__init__("Poll Pow vs. RPM", app_or_ipv4)

        self._sps = []
        self._sps.extend(sps)

        self._ramp_time = ramp_time
        self._poll_time = poll_time
        self._app = None
        self._results = []

    def poll(self):

        self._init_app()

        for sp in self._sps:
            self._log("Testing sp: %s %% power" % str(sp))

            try:
                ave, pvs = self._test_sp(sp, self._ramp_time, self._poll_time, 1)
            except:
                self._log_err("Error occurred running test")
            else:
                self._results.append((sp, ave, pvs))  # 3 tuple (sp, ave, pvs)

        # sort here by set point
        self._results.sort(key=lambda v: v[0])

    def _test_sp(self, sp, ramp_time, poll_time, poll_interval):

        app = self._app
        _time = time

        self._log("Setting agitation to", sp)
        app.login()
        app.setag(1, sp)

        self._log("Initializing test. Ramping for %d seconds." % ramp_time)
        sleep(ramp_time)
        end = _time() + poll_time

        next_log_time = _time()

        pvs = []
        try:
            while True:
                pv, actual_sp = app.getmanagvals()

                if actual_sp != sp:
                    raise PollError("Warning sp doesn't match! %s!=%s" % (str(sp), str(actual_sp)))

                pvs.append(pv)
                t = _time()

                if t > end:
                    break
                elif t > next_log_time:
                    next_log_time += 10
                    self._log("Polling. AgPV: %.2f SP: %.2f" %
                              (float(pv), float(actual_sp)))
                    self._log("%d of %d seconds passed." % (poll_time - (end - t), poll_time))

                sleep(poll_interval)
        except KeyboardInterrupt:
            self._log("Got KeyboardInterrupt, skipping test.")
        return _ave(pvs), pvs

    def _copy_xl_data(self, cells):
        # first loop, copy sps.

        self._log("Preparing averaged data for transfer")
        xldata = [(sp, pv) for sp, pv, _ in self._results]

        self._log("Transfering data")
        cells.Range(cells(3, 2), cells(2 + len(xldata), 3)).Value = xldata

        # Loop again, copy *all* data
        self._log("Preparing all data for transfer")
        for i, (sp, _, pvs) in enumerate(self._results, 5):
            cells(2, i).Value = str(sp)
            end = len(pvs) + 2
            cells.Range(cells(3, i), cells(end, i)).Value = [(x,) for x in pvs]

        return xldata

    def _plot_chart(self, ws, xrng, yrng):

        # imports here to avoid having to load wincom every time the script loads.
        from officelib.xllib.xlcom import CreateChart, FormatChart, CreateDataSeries

        chart = CreateChart(ws)
        CreateDataSeries(chart, xrng, yrng, "Pow (%) vs RPM")
        FormatChart(chart, None, "Pow (%) vs RPM", "Power (%)", "RPM", None, False)
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

    def toxl(self):

        self._log("Initializing Excel for power curve")
        xl, wb, ws, cells = self._init_xl()
        try:
            xldata = self._copy_xl_data(cells)
            xrng, yrng = self._calc_xl_rngs(2, ws, xldata)

            self._log("Initializing chart")
            chart = self._plot_chart(ws, xrng, yrng)

            name = "Pow v. RPM"
            self._log("Moving chart to new ws:", name)

            chart.Location(1, name)  # move to new worksheet
            axes = chart.Axes(AxisGroup=2)  # xlPrimary
            axes(1).HasMajorGridlines = True
            axes(2).HasMajorGridlines = True
        except:
            self._log_err("Error occurred during data transfer")
        finally:
            self._log("Done.")
            wb.Save()
            wb.Close(True)  # this also saves. better safe than sorry.
            xl.Quit()


class StartupPoller(_Poller):

    def __init__(self, app_or_ipv4='192.168.1.6'):
        super().__init__("Startup Test", app_or_ipv4)
        self._results = []

    def test_startup(self, hint=None, iters=3, incr=0.1, timeout=30, pre_pause=5, poll_time=30):
        """

        @param hint: setpoint to start startup test at.
        @param incr: increase setpoint by this amount every iter
        @param timeout: wait this long to detect RPM before increasing SP
        """
        if hint is None:
            hint = 0.2

        sp = hint
        self._init_app()

        app = self._app
        _sleep = sleep
        _time = time

        self._log("Beginning Startup Test")
        test_no = 1
        while True:

            self._log("Turning agitation off and sleeping %s seconds" % pre_pause)

            app.login()
            app.setag(2, 0)

            _sleep(pre_pause)

            # make sure agitation is stopped!
            # alert if not stopped after 60 sec
            # should not ever happen if off mode is set correctly

            alert_time = _time() + 60

            if app.getagpv() > 0:
                self._log("Waiting for agitation to stop")
            while app.getagpv() > 0:
                if _time() > alert_time:
                    raise PollError("Error: agitation did not stop.")
                _sleep(0.1)

            self._log("Initializing agitation and beginning test")
            app.setag(1, sp)
            passed = self._poll_startup(sp, timeout, pre_pause)

            if passed:
                self._log("Got passing test, polling pv for %s seconds" % poll_time)
                pvs = self._poll_pv(10, poll_time, 1)
                self._log("Got startup result for test #%d: wheel started at %s%% power" % (test_no, sp))
                self._results.append((sp, pvs))
                test_no += 1
                sp = hint
                if test_no > iters:
                    break
            else:

                if sp >= 100:
                    raise PollError("Agitation did not start at 100% power")
                self._log("Agitation did not start. Increasing setpoint.")
                sp += incr

    def _poll_startup(self, sp, timeout, pre_pause):

        _sleep = sleep
        _time = time
        app = self._app

        _sleep(pre_pause)
        end = _time() + timeout
        self._log("Beginning Startup Polling")
        while True:
            pv, ret_sp = app.getmanagvals()

            if ret_sp != sp:
                raise PollError("SP != actual setpoint")
            elif pv > 0:
                return True
            elif _time() > end:
                return False

            _sleep(1)

    def _poll_pv(self, startup_time, poll_time, interval):
        _sleep = sleep
        _time = time
        app = self._app

        _sleep(startup_time)
        end = _time() + poll_time

        pvs = []
        while _time() < end:
            pv = app.getagpv()
            pvs.append(pv)
            _sleep(interval)

        return pvs


class LowestTester(_Poller):
    def __init__(self, app_or_ipv4='192.168.1.6'):
        super().__init__("Low RPM Test", app_or_ipv4)
        self._results = []

    def test_lowest(self, start_at=10, iters=3, decr=0.1, timeout=30, pre_pause=5):
        """
        @param start_at: % power to start at to initialize agitation.
        @param decr: decrease power by this much each test
        @param pre_pause: wait for this long before starting to poll RPM
        """

        self._init_app()
        app = self._app
        _sleep = sleep
        _time = time

        sp = start_at

        self._log("Beginning Startup Test")
        test_no = 1
        lastpvs = ()
        while True:

            app.login()
            app.setag(1, sp)
            _sleep(2)

            # make sure agitation is stopped!
            # alert if not stopped after 60 sec
            # should not ever happen if off mode is set correctly

            alert_time = _time() + 60
            if app.getagpv() <= 0:
                self._log("Waiting for agitation to start")
            while app.getagpv() <= 0:
                if _time() > alert_time:
                    raise PollError("Error: agitation did not start.")
                _sleep(0.1)

            try:
                stopped, pvs = self._poll_lowest(sp, timeout, pre_pause)
            except PollError:
                self._log_err("Error running test")
                test_no += 1
                if test_no > iters:
                    break
                continue

            if stopped:
                result = sp + decr
                self._log("Got lowest result for test #%d: wheel started at %s%% power" % (test_no, result))
                self._results.append((result, lastpvs))
                test_no += 1
                sp = start_at
                if test_no > iters:
                    break
            else:
                self._log("Agitation did not stop. Lowering setpoint.")
                lastpvs = pvs
                if sp <= 0:
                    raise PollError("Agitation did not stop at 0% power")
                sp -= decr

    def _poll_lowest(self, sp, timeout, pre_pause):

        _sleep = sleep
        _time = time
        app = self._app

        _sleep(pre_pause)
        end = _time() + timeout
        pvs = []
        while True:
            pv, ret_sp = app.getmanagvals()
            pvs.append(pv)

            if ret_sp != sp:
                raise PollError("SP != actual setpoint")
            elif pv <= 0:
                return True, None
            elif _time() > end:
                return False, pvs

            _sleep(1)


def _ave(o):
    return sum(o) / len(o)


def test():
    p = StartupPoller()
    # p.test_lowest(10, 3, 1, 10, 5)
    p.test_startup(5, 3, 1, 10, 5, 10)


if __name__ == '__main__':
    test()
