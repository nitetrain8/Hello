"""

Created by: Nathan Starkweather
Created on: 10/21/2014
Created in: PyCharm Community Edition


"""
from officelib.const import xlToRight, xlByRows, xlDown, xlXYScatterLines
from officelib.xllib.xlcom import CreateChart, FormatChart, xlObjs, CreateDataSeries, HiddenXl
from officelib.xllib.xladdress import chart_range_strs
from re import match
from os.path import split as path_split
from officelib.xllib.xlcom import AddTrendlines


__author__ = 'Nathan Starkweather'


from hello import HelloThing, HelloError, HelloApp, Logger
from time import time as _time, sleep as _sleep


class KLAError(HelloError):
    pass


class KLATest(Logger, HelloThing):
    """ KLA test runner designed ground-up to work for
    *3L Mag Wheel* only! If using any other setup, review code to verify
     it will work correctly!!!

     Since mag drive uses headspace to "sparge" the vessel with oxygen,
     no operator activity with tubing, gases, etc is necessary in certain
     circumstances.

     This class ASSUMES THE FOLLOWING:

     * 1.3 hello software
     * Logger settings are correct
     * N2 gas is connected to a tank with sufficient volume, to N2 AND O2 inlets
     * Air is connected to a compressor (or tank w/ sufficient volume) to air inlet
     * Vessel is inserted in reactor, with Main and Micro gas lines connected
     * All ports on the top of the vessel are closed
     * Filter oven is only open line for gas to escape
     * Vessel has Main Gas connector on L-plate snipped.
     * Vessel has Micro Gas connector on L-plate intact!
    """
    def __init__(self, app_or_ipv4, vessel_max=4, max_mfc_rate=0.5, setup_timeout=None):
        Logger.__init__(self, "KLATest")
        HelloThing.__init__(self, app_or_ipv4)
        self._max_mfc_rate = max_mfc_rate
        self._vessel_max = vessel_max
        self._setup_timeout = setup_timeout or (2 ** 31 - 1)
        self._init_app()

        # temp hack to solve connection issues 10/22/14
        import types
        klatest = self
        klatest._newcons = 0

        def reconnect(self):
            klatest._log("Connection reconnecting")
            klatest._newcons += 1
            # This is not a typo
            # need to call super method, but can't use super() here because it
            # will refer to super(KLATest) instead!
            HelloApp.reconnect(self)
            self.login()
        self._app.reconnect = types.MethodType(reconnect, self._app)

    def setup(self):

        self._log("Initializing KLA Setup")
        app = self._app
        app.login()
        app.setag(1, 50)
        app.setdo(1, 0, 500)

        start = _time()

        self._log("Begin setup. Waiting for DO < 20%")
        log_time = _time() + 10
        while app.getdopv() > 20:
            t = _time()
            if t > log_time:
                log_time = int(t) + 10
                self._log("Waiting for DO to fall below 20.")
                self._log("%d seconds: %.1f%% DO" % (t - start, app.getdopv()))
            _sleep(1)

        app.setdo(2, 0, 0)
        app.setmg(2, 0)

    def clear_headspace(self, media_volume):

        self._log("Preparing to purge headspace")

        # math
        headspace = self._vessel_max - media_volume
        sleep_time = headspace / self._max_mfc_rate * 60

        app = self._app
        app.login()
        app.setdo(2, 0)
        app.setmg(1, self._max_mfc_rate)

        self._log("Purging headspace at %.3f LPM for %d seconds" % (self._max_mfc_rate, sleep_time))

        time = _time
        sleep = _sleep
        t = time()
        end = t + sleep_time
        log_time = int(t) + 10

        while t < end:
            if t > log_time:
                log_time = int(t) + 10
                left = int(end - t)
                self._log("Purging headspace. %s seconds remaining" % left)
            t = time()
            sleep(5)

        # login again in case sleep_time was long
        app.login()
        app.setmg(2, 0)

    def run(self, volume, experiments):
        # batches is list of batch names
        batches = self.run_experiments(volume, experiments)
        batch_list = self._app.getbatches(True)

        reports = []
        for b in batches:
            id = batch_list.getbatchid(b)
            r = self._app.getdatareport_bybatchid(id)
            reports.append((b, id, r))
        return reports

    def run_experiments(self, volume, experiments):
        """
        @param volume: volume of media in L
        @param experiments: 3 tuple (ag_mode, ag_sp, flow_rate)
        @type experiments: ((int | float, int | float, int | float)) | list[(int | float, int | float, int | float)]
        @return: list of batches
        @rtype: list[str]
        """
        batches = []

        self._log("Running %d experiments." % len(experiments))
        for i, (mode, sp, flowrate) in enumerate(experiments, 1):

            self._log("Running test %d of %d" % i, len(experiments))

            try:
                self.setup()
            except KeyboardInterrupt:
                self._log_err("Got keyboard interrupt, skipping setup.")

            try:
                self.clear_headspace(volume)
            except KeyboardInterrupt:
                self._log_err("Got keyboard interrupt, skipping headspace purge.")

            try:
                b = self.experiment(mode, sp, flowrate)
                batches.append(b)
            except KeyboardInterrupt:
                self._log_err("Got keyboard interrupt, skipping test.")
                continue
            finally:
                mv = self._app.gpmv()
                if mv['do']['mode'] != 2:
                    while True:
                        try:
                            self._app.login()
                            self._app.setdo(2, 0, 0)
                            break
                        except Exception:
                            self._log_err("Error shutting down test.")
                            self._app.reconnect()

        return batches

    def experiment(self, ag_mode, ag_sp, flow_rate):
        """
        @param flow_rate: flow rate in *mL per min*
        """
        app = self._app
        app.login()

        self._log("Initializing Agitation with mode=%s sp=%s." % (ag_mode, ag_sp))
        app.setag(ag_mode, ag_sp)

        # if setpoint is auto mode, wait for pv to reach correct value
        if ag_mode == 0:
            timeout = 10 * 60
            end = _time() + timeout
            log_time = _time() + 10
            while True:
                pv = app.getagpv()
                if ag_sp - 1 < pv < ag_sp + 1:
                    break
                t = _time()
                if t > log_time:
                    log_time = int(t) + 10
                    self._log("Waiting for Agitation to reach setpoint. PV = %d." % app.getagpv())
                _sleep(1)
                if t > end:
                    raise KLAError("Agitation didn't reach setpoint.")

        app.setmg(1, flow_rate / 1000)

        time = _time

        start = time()
        timeout = start + 14 * 60

        self._log("Beginning KLA Experiment.")

        batch_name = "KLA%s-%s-%s" % (ag_mode, ag_sp, flow_rate)

        self._log("Starting new batch named '%s'." % batch_name)
        if app.batchrunning():
            app.endbatch()
        app.startbatch(batch_name)

        log_time = time() + 10
        while True:
            t = time()
            pv = app.getdopv()
            if t > log_time:
                self._log("Test running, %d seconds passed. DO PV = %.1f." % (t - start, pv))
                log_time = t + 10
            if t > timeout:
                break
            if pv > 90:
                break

        self._log("Test finished. DO PV = %.1f after %d seconds." % (app.getdopv(), time() - start))

        self._log("Ending batch")
        app.endbatch()
        return batch_name


def _insert_time_col(ws, cells, col):

    from officelib.xllib.xladdress import cellStr, cellRangeStr

    end_row = cells(2, col - 1).End(xlDown).Row
    ws.Columns(col).Insert(Shift=xlToRight)
    formula = "=(%s-%s) * 24" % (cellStr(2, col - 1), cellStr(2, col - 1, 1, 1))
    cells(2, col).Value = formula
    fill_range = cellRangeStr(
        (2, col), (end_row, col)
    )

    af_rng = cells.Range(fill_range)
    cells(2, col).AutoFill(af_rng)

    ws.Columns(col).NumberFormat = "0.00"


def _insert_ln_col(ws, cells, col):
    from officelib.xllib.xladdress import cellStr, cellRangeStr

    end_row = cells(2, col - 1).End(xlDown).Row
    ws.Columns(col).Insert(Shift=xlToRight)
    formula = "=-LN(100-%s)" % cellStr(2, col - 1)
    cells(2, col).Value = formula
    fill_range = cellRangeStr(
        (2, col), (end_row, col)
    )

    af_rng = cells.Range(fill_range)
    cells(2, col).AutoFill(af_rng)

    ws.Columns(col).NumberFormat = "0.00000"


class _dbgmeta(type):
    def __new__(mcs, name, bases, kwargs):
        from types import FunctionType

        def decorator(f):
            def wrapper(*args, **kwargs):
                print("Function called:", f.__name__)
                rv = f(*args, **kwargs)
                print("Function returned:", f.__name__)
                return rv
            return wrapper

        for k, v in kwargs.items():
            if isinstance(v, FunctionType):
                kwargs[k] = decorator(v)

        # fuck it
        for k, v in globals().items():
            if isinstance(v, FunctionType):
                globals()[k] = decorator(v)

        return type.__new__(mcs, name, bases, kwargs)


class KLAAnalyzer():
    def __init__(self, files):
        self._files = files
        self._xl, self._wb, self._ws, self._cells = xlObjs()
        self._ws.Name = "Data"
        self._ln_chart = None
        self._linear_chart = None
        self._current_col = 1

    def analyze_all(self):
        self._init_linear_chart()
        self._init_ln_chart()
        for i, f in enumerate(self._files, 1):
            print("Analyzing file #%d of %d" % (i, len(self._files)))
            self.analyze_file(f)

        self._linear_chart.Location(1, "Time v DOPV")
        self._ln_chart.Location(1, "Time v LN DOPV")

        for chart in (self._ln_chart, self._linear_chart):
            try:
                AddTrendlines(chart)
            except:
                print("Couldn't add trendlines")

    def close(self):
        self._xl = self._wb = self._ws = self._cells = None

    def analyze_file(self, file):

        # identifying name for chart/test/series
        file = file.replace("/", "\\")
        print("Analyzing file:", file[file.rfind("\\") + 1:])
        try:
            mode, ag, gas_flow = match(r"kla(\d*)-(\d*)-(\d*)", path_split(file)[1]).groups()
        except TypeError:
            name = "KLA"
        else:
            if mode == '0':
                unit = " RPM"
            else:
                unit = "% Power"
            name = "KLA %s%s %s mLPM" % (ag, unit, gas_flow)

        print("Processing Worksheet.")
        xl_name = self.process(file, name)
        print("Adding data to compiled data set.")
        self.add_to_compiled(xl_name, name)

    def _init_linear_chart(self):
        chart = CreateChart(self._ws, xlXYScatterLines)
        FormatChart(chart, None, "KLA Data (compiled)", "Time(hr)", "DOPV(%)")
        self._linear_chart = chart

    def _init_ln_chart(self):
        chart = CreateChart(self._ws, xlXYScatterLines)
        FormatChart(chart, None, "KLA Data (compiled, -LN(100-DOPV))", "Time(hr)", "-LN(100-DOPV)")
        self._ln_chart = chart

    def add_to_compiled(self, file, series_name):
        xl, wb, ws, cells = xlObjs(file, visible=False)

        with HiddenXl(xl):
            # copy data to new ws
            do_cell = cells.Find("DOPV(%)", cells(1, 1), SearchOrder=xlByRows)
            fleft = do_cell.Column
            fright = cells(2, fleft).End(xlToRight).Column
            fbottom = do_cell.End(xlDown).Row

            value = cells.Range(cells(1, fleft), cells(fbottom, fright)).Value
            trng = self._cells.Range(self._cells(1, self._current_col),
                                     self._cells(fbottom, self._current_col + fright - fleft))
            trng.Value = value

            # add LN chart
            if self._ln_chart is None:
                self._init_ln_chart()
            chart = self._ln_chart
            xrng, yrng = chart_range_strs(self._current_col, self._current_col + 1, 2, fbottom, self._ws.Name)
            CreateDataSeries(chart, xrng, yrng, series_name)

            # add linear chart
            if self._linear_chart is None:
                self._init_linear_chart()
            chart = self._linear_chart
            xrng, yrng = chart_range_strs(self._current_col, self._current_col + 2, 2, fbottom, self._ws.Name)
            CreateDataSeries(chart, xrng, yrng, series_name)

        self._current_col += fright - fleft + 2

    def process(self, file, chart_name):
        """
        Analyzing data is ugly. Analyze 'file', where 'file' is a csv file
         corresponding to a batch report.
        """

        xl, wb, ws, cells = xlObjs(file, visible=False)
        with HiddenXl(xl):
            do_cell = cells.Find(What="DOPV(%)", After=cells(1, 1), SearchOrder=xlByRows)
            xcol = do_cell.Column + 1
            end_row = do_cell.End(xlDown).Row
            _insert_time_col(ws, cells, xcol)
            _insert_ln_col(ws, cells, xcol + 2)

            # ln v time for specific chart
            xrng, yrng = chart_range_strs(xcol, xcol + 2, 2, end_row, ws.Name)
            chart = CreateChart(ws, xlXYScatterLines)
            CreateDataSeries(chart, xrng, yrng, "KLA")

            FormatChart(chart, None, chart_name, "Time(min)", "-LN(DO PV (%))", True)
            chart.Location(1)

            # file should always be csv, but be generic just in case.
            save_name = file.replace(file[file.rfind("."):], '.xlsx')
            wb.SaveAs(save_name, AddToMru=True)

        return save_name



def __test_analyze_kla():
    file = "C:\\Users\\Public\\Documents\\PBSSS\\KLA Testing\\PBS 3 mech wheel\\kla0-10-200 id-35 27-10-14.csv"
    # analyze_kla(file)

tka = __test_analyze_kla


if __name__ == '__main__':
    # test = KLATest('192.168.1.6')
    # test.setup()
    __test_analyze_kla()
