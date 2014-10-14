"""

Created by: Nathan Starkweather
Created on: 10/13/2014
Created in: PyCharm Community Edition


"""
from abc import abstractmethod, ABC

__author__ = 'Nathan Starkweather'

from hello.hello import HelloApp
from time import time, sleep
from officelib.xllib.xladdress import cellRangeStr


class PIDBadError(Exception):
    pass


def _flattenify(*args):
    return tuple(args)


class PIDTest(ABC):

    _passmap = {
        "No": False,
        "Yes": True,
        True: True,
        False: False,
        1: True,
        0: False
    }

    app = None

    def __init__(self, p, i, d, sp, app_or_ipv4='192.168.1.6'):
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

        Note subclass must override:
            group: group to send to set_mode call (eg 'agitation', 'temperature', ...)
            get_values: return pv, sp, and any other values desired
            check_begin: return bool as to whether to begin the test or raise an exception.

        Subclass may override:
            settings: iterable of 3-tuples: (group, setting, value) to send to HelloApp.set_config()
        """

        self.xrng = ""
        self.yrng = ""
        self.p = p
        self.i = i
        self.d = d
        self.passed = False
        self.data = None
        self.pvs = None
        self.settings = ()
        self.group = ""
        self.sp = sp

        if type(app_or_ipv4) is HelloApp:
            self.app = app_or_ipv4
        else:
            self.app = HelloApp(app_or_ipv4)

    @abstractmethod
    def check_begin(self, app):
        """
        Abstract. Raise an exception if the test shouldn't begin.
        """
        return True

    def _init_settings(self):

        if not self.settings:
            return

        app = self.app
        for grp, set, val in self.settings:
            app.login()
            app.setconfig(grp, set, val)

    @abstractmethod
    def get_values(self, app):
        """
        Abstract. Must return pv, sp, and optionally others.
        PV and SP must be first two values returned, in that order.

        Function is passed the HelloApp object, which may be accessed
        to return any values desired.
        """
        return 0, 0

    def off_to_auto(self, margin=0.1, settle_time=3600, poll_interval=10, ramp_timeout=7200):
        """
        @param margin: SP +/- margin to begin "settling"
        @type margin: int | float
        @param settle_time: seconds to keep polling after reaching temp +/- settle_margin
        @type settle_time: int
        """

        # Initialize bioreactor setting state
        self._init_settings()

        # unpack some items to speed up the function
        app = self.app
        sp = self.sp
        pvs = self.pvs = []
        _time = time
        _sleep = sleep
        get_values = self.get_values
        timeout_time = ramp_timeout + _time()

        passed = True

        settle_min = sp - margin
        settle_max = sp + margin

        pv, sp, *_ = self.get_values(app)

        # Turn the thing off
        app.login()
        app.set_mode(self.group, 2, 0)

        # arbitrary; test runner is responsible for
        # resetting reactor test state; don't rely on this.
        _sleep(5)

        # turn the thing on.
        app.login()
        app.set_mode(self.group, 0, self.sp)

        self.check_begin(app)

        # first loop: poll until pv within margin
        while True:
            pv, actual_sp, *others = get_values(app)

            if actual_sp != sp:
                raise PIDBadError("SP changed during run.")

            t = _time()

            if others:
                v = _flattenify(t, pv, *others)
            else:
                v = (t, pv)

            pvs.append(v)

            if pv > settle_min:
                break
            elif t > timeout_time:
                passed = False
                break

            _sleep(poll_interval)

        # second loop: poll for one hour
        end = _time() + settle_time

        while True:
            pv, actual_sp, *others = get_values(app)

            if actual_sp != sp:
                raise PIDBadError("SP changed during run.")

            t = _time()

            if others:
                v = _flattenify(t, pv, *others)
            else:
                v = (t, pv)

            pvs.append(v)

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
            raise PIDBadError("Can't plot- no data!")

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
