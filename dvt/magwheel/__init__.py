"""

Created by: Nathan Starkweather
Created on: 10/15/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from hello import HelloApp
from hello.logger import Logger
from time import time, sleep


class FailTest(Exception):
    pass


class Step16(Logger):
    def __init__(self, app_or_ipv4='192.168.1.6'):
        Logger.__init__(self, "Mag DVT Step 16")
        self._app = HelloApp(app_or_ipv4)

    def _test_ramp(self, app, mode, sp, target):
        _time = time
        _sleep = sleep
        app.setag(2, 0)
        val_getter = (app.getautoagvals, app.getmanagvals)[mode]
        self._log("Sleeping for 35 seconds")
        _sleep(35)
        # debug
        # while app.getagpv() > 0:
        #     _sleep(1)
        if app.getagpv() > 0:
            raise FailTest("Agitation did not stop")
        self._log("Starting test")
        app.setag(mode, sp)
        start = _time()
        while True:
            pv, ret_sp = val_getter()
            if ret_sp != sp:
                raise FailTest("SP doesn't match")
            if _time() - start > 180:
                raise FailTest("Agitation did not reach set point within 180 seconds")
            if pv > target - 1:
                break
            _sleep(0.5)
        return _time() - start

    def _test_ramps(self, app, mode, sp, target, iters):
        """
        @param app: HelloApp object
        @param mode: 0 (auto) or 1 (man)
        @param sp: setpoint in RPM (auto) or % power (man)
        @param target: target setpoint.
        @param iters: number of tests to run
        @return: list of time to sp-1
        """
        results = []
        mode_name = ("Auto", "Manual")[mode]

        logstr = "%s ramp test %d RPM #%%d of %d" % (mode_name, target, iters)
        for i in range(1, iters + 1):
            self._log(logstr % i)
            try:
                r = self._test_ramp(app, mode, sp, target)
            except FailTest:
                self._log_err("Test %d failed" % i)
                r = -1
            except KeyboardInterrupt:
                self._log("Got keyboard interrupt: skipping test")
                r = -1
            else:
                self._log("Successful Test: %d seconds" % r)
            results.append(r)

        return results

    def _test_man_ramps(self, app, sp, target, iters):
        """ Currently unused. """
        results = []
        mode_name = "Manual"

        logstr = "%s ramp test %d RPM #%%d of %d" % (mode_name, target, iters)
        for i in range(1, iters + 1):
            self._log(logstr % i)
            try:
                r = self._test_man_ramp(app, sp, target)
            except FailTest:
                self._log_err("Test %d failed" % i)
                r = -1
            else:
                self._log("Successful Test: %d seconds" % r)
            results.append(r)

        return results

    def _test_man_ramp(self, app, sp, target):
        """ Currently unused. """
        _time = time
        _sleep = sleep
        app.setag(2, 0)
        self._log("initializing RPM")
        # debug
        while app.getagpv() > 0:
            _sleep(1)
        if app.getagpv() > 0:
            raise FailTest("Agitation did not stop")
        self._log("Starting test")
        app.setag(1, sp)
        start = _time()
        _sleep(1)
        while True:
            pv, ret_sp = app.getmanagvals()
            if ret_sp != sp:
                raise FailTest("SP doesn't match")
            if _time() - start > 180:
                raise FailTest("Agitation did not reach set point within 180 seconds")
            if pv > target - 1:
                break
            _sleep(0.5)
        return _time() - start

    def run(self, pow10rpm=6.1, pow50rpm=75):
        """
        @param pow10rpm: manual power % for 10 rpm
        @param pow50rpm: manual power % for 50 rpm
        """
        app = self._app
        app.login()

        self._log("Beginning test 16: Agitation Ramp Controller Logic")
        self._log("Beginning 15 RPM ramp test")
        r_auto_15 = self._test_ramps(app, 0, 15, 15, 10)
        self._show_results(r_auto_15, "Auto", 15)

        self._log("Beginning 30 RPM ramp test")
        r_auto_30 = self._test_ramps(app, 0, 30, 30, 10)
        self._show_results(r_auto_30, "Auto", 30)

        self._log("Beginning Manual 10 RPM ramp test")
        r_man_10 = self._test_ramps(app, 1, pow10rpm, 10, 10)
        self._show_results(r_man_10, "Manual", 10)

        self._log("Beginning Manual 50 RPM ramp test")
        r_man_50 = self._test_ramps(app, 1, pow50rpm, 50, 10)
        self._show_results(r_man_50, "Manual", 50)

        self._log()
        self._log()
        self._log("Final Results:")
        self._log()
        self._show_results(r_auto_15, "Auto", 15)
        self._show_results(r_auto_30, "Auto", 30)
        self._show_results(r_man_10, "Manual", 10)
        self._show_results(r_man_50, "Manual", 50)

    def _show_results(self, results, mode_name, target):
        for i, r in enumerate(results, 1):
            self._log("%s mode %d RPM test #%d: %d" % (mode_name, target, i, r))
        self._log()


if __name__ == '__main__':
    Step16().run()
