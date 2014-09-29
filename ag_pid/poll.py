"""

Created by: Nathan Starkweather
Created on: 09/26/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from hello.ag_pid.logger import Logger
from hello.hello import HelloApp
from time import time, sleep
from datetime import datetime

_now = datetime.now


class PollError(Exception):
    pass


class Poller(Logger):

    def __init__(self, sps, ramp_time=40,
                 poll_time=360, app_or_ipv4='192.168.1.6'):
        Logger.__init__(self, "Poll PV vs. RPM")

        self._sps = []
        for s in sps:
            self._sps.append(s)

        self._ramp_time = ramp_time
        self._app_or_ipv4 = app_or_ipv4
        self._poll_time = poll_time
        self._app = None
        self._results = []

    def poll(self):

        if type(self._app_or_ipv4) is HelloApp:
            self._app = self._app_or_ipv4
        else:
            self._app = HelloApp(self._app_or_ipv4)

        for sp in self._sps:
            self._log("Testing sp: %s %% power" % str(sp))

            try:
                ave, pvs = self._test_sp(sp, self._ramp_time, self._poll_time, 1)
            except:
                self._log_err("Error occurred running test")
            else:
                self._results.append((sp, ave, pvs))  # 3 tuple (sp, ave, pvs)

    def _test_sp(self, sp, ramp_time, poll_time, poll_interval):

        app = self._app
        _time = time

        self._log("Setting agitation to", sp)
        app.login()
        app.setag(1, sp)

        self._log("Initializing test. Ramping for %d seconds." % ramp_time)
        sleep(ramp_time)
        end = _time() + poll_time

        next_log_time = _time() + 30

        pvs = []
        while True:
            pv, realsp = app.getmanagvals()

            if realsp != sp:
                raise PollError("Warning sp doesn't match! %s!=%s" % (str(sp), str(realsp)))

            self._log("Polling. AgPV: %.2f SP: %.2f" % (float(pv), float(realsp)))
            pvs.append(pv)
            t = _time()

            if t > end:
                break
            elif t > next_log_time:
                next_log_time = t + 30
                self._log("Polling. %d out of %d seconds remain" % (end - t, poll_time))

            sleep(poll_interval)

        return _ave(pvs), pvs

    def copy(self):

        cls = type(self)
        new = cls(self._sps, self._ramp_time, self._poll_time, self._app_or_ipv4)
        new._results = self._results.copy()
        return new

    def _init_xl(self):
        from officelib.xllib.xlcom import xlObjs

        date = _now().strftime("%y%m%d%H%M%S")
        name = "Poll Results " + date + ".xlsx"
        dir = "C:\\Users\\Public\\Documents\\PBSSS\\Agitation\\Mag Wheel PID\\"
        fpth = dir + name
        xl, wb, ws, cells = xlObjs()
        wb.SaveAs(fpth)
        return xl, wb, ws, cells

    def toxl(self):

        self._log("Initializing Excel")
        xl, wb, ws, cells = self._init_xl()

        self._log("Preparing data for transfer")
        xldata = [(sp, pv) for sp, pv, _ in self._results]
        xldata.sort(key=lambda t: t[0])

        self._log("Transfering data")
        cells.Range(cells(3, 2), cells(2 + len(xldata), 3)).Value = xldata

        self._log("Done.")


def _ave(o):
    return sum(o) / len(o)
