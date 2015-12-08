"""

Created by: Nathan Starkweather
Created on: 10/21/2014
Created in: PyCharm Community Edition


"""
from officelib.const import xlToRight, xlByRows, xlDown, xlXYScatterLines
from officelib.xllib.xlcom import CreateChart, FormatChart, xlObjs, CreateDataSeries, HiddenXl, AddTrendlines
from officelib.xllib.xladdress import chart_range_strs, cellStr, cellRangeStr
from pysrc.snippets import safe_pickle, unique_name

from re import match
from os.path import split as path_split
from datetime import datetime
from os import makedirs
import traceback
from time import time as _time, sleep as _sleep


__author__ = 'Nathan Starkweather'

try:
    from hello import HelloError, HelloApp, open_hello
    from logger import BuiltinLogger
except ImportError:
    from hello.hello import HelloError, HelloApp, open_hello
    from hello.logger import BuiltinLogger


_docroot = "C:\\.replcache\\"


class KLAError(HelloError):
    pass


class SkipTest(Exception):
    pass


class KLAReport():
    def __init__(self, name=None, id=None, contents=None, filename=None):
        self.name = name
        self.id = id
        self.contents = contents
        self.filename = filename

    def read(self):
        return self.contents


class MechKLATest():
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
    def __init__(self, ipv4, vessel_max=4, max_mfc_rate=0.5, setup_timeout=None):
        self.logger = BuiltinLogger("MechKLATest")
        self._max_mfc_rate = max_mfc_rate
        self._vessel_max = vessel_max
        self._setup_timeout = setup_timeout or (2 ** 31 - 1)
        self.app = HelloApp(ipv4)
        self._reports = None

    def setup(self):

        self.logger.info("Initializing KLA Setup")

        app = self.app
        app.login()
        app.setag(1, 50)
        app.setdo(1, 0, 500)

        start = _time()

        self.logger.info("Begin setup. Waiting for DO < 20%")
        log_time = _time() + 10
        while app.getdopv() > 20:
            t = _time()
            if t > log_time:
                log_time = int(t) + 10
                self.logger.info("Waiting for DO to fall below 20.")
                self.logger.info("%d seconds: %.1f%% DO" % (t - start, app.getdopv()))
            _sleep(1)

        app.setdo(2, 0, 0)
        app.setmg(2, 0)

    def clear_headspace(self, media_volume):

        self.logger.info("Preparing to purge headspace")

        # math
        headspace = self._vessel_max - media_volume
        sleep_time = headspace / self._max_mfc_rate * 60

        app = self.app
        app.login()
        app.setdo(2, 0)
        app.setmg(1, self._max_mfc_rate)

        self.logger.info("Purging headspace at %.3f LPM for %d seconds" % (self._max_mfc_rate, sleep_time))

        time = _time
        sleep = _sleep
        t = time()
        end = t + sleep_time
        log_time = int(t) + 10

        while t < end:
            if t > log_time:
                log_time = int(t) + 10
                left = int(end - t)
                self.logger.info("Purging headspace. %s seconds remaining" % left)
            t = time()
            sleep(5)

        # login again in case sleep_time was long
        app.login()
        app.setmg(2, 0)

    def run(self, volume, experiments):
        # batches is list of batch names
        batches = self.run_experiments(volume, experiments)

        if self._reports is None:
            reports = self._reports = []
        else:
            reports = self._reports

        batch_list = self.app.getBatches()

        for name in batches:
            id = batch_list.getbatchid(name)
            r = self.app.getdatareport_bybatchid(id)
            b = KLAReport(name, id, r)
            reports.append(b)
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

        self.logger.info("Running %d experiments." % len(experiments))
        for i, (mode, sp, flowrate) in enumerate(experiments, 1):

            self.logger.info("Running test %d of %d" % (i, len(experiments)))

            try:
                self.setup()
            except KeyboardInterrupt:
                self.logger.error("Got keyboard interrupt, skipping setup.")

            try:
                self.clear_headspace(volume)
            except KeyboardInterrupt:
                self.logger.error("Got keyboard interrupt, skipping headspace purge.")

            try:
                b = self.experiment(mode, sp, flowrate, volume)
                batches.append(b)
            except KeyboardInterrupt:
                self.logger.error("Got keyboard interrupt, skipping test.")
                continue
            finally:
                mv = self.app.gpmv()
                if mv['do']['mode'] != 2:
                    while True:
                        try:
                            self.app.login()
                            self.app.setdo(2, 0, 0)
                            break
                        except Exception:
                            self.logger.error("Error shutting down test.")
                            self.app.reconnect()

        return batches

    def experiment(self, ag_mode, ag_sp, flow_rate, volume):
        """
        @param flow_rate: flow rate in *mL per min*
        """
        app = self.app
        app.login()
        time = _time

        self.logger.info("Initializing Agitation with mode=%s sp=%s." % (ag_mode, ag_sp))
        app.setag(ag_mode, ag_sp)

        # if setpoint is auto mode, wait for pv to reach correct value
        if ag_mode == 0:
            timeout = time() + 10 * 60
            log_time = time() + 10
            while True:
                pv = app.getagpv()
                if ag_sp - 1 < pv < ag_sp + 1:
                    break
                t = time()
                if t > log_time:
                    log_time = int(t) + 10
                    self.logger.info("Waiting for Agitation to reach setpoint. PV = %d." % app.getagpv())
                if t > timeout:
                    raise KLAError("Agitation didn't reach setpoint.")
                _sleep(1)

        app.setmg(1, flow_rate / 1000)

        self.logger.info("Beginning KLA Experiment.")

        batch_name = "kla%s-%s-%s-%s" % (ag_mode, volume, ag_sp, flow_rate)

        self.logger.info("Starting new batch named '%s'." % batch_name)
        if app.batchrunning():
            app.endbatch()
        app.startbatch(batch_name)

        start = time()
        end = start + 14 * 60
        log_time = start + 10
        while True:
            t = time()
            pv = app.getdopv()
            if t > log_time:
                self.logger.info("Test running, %d seconds passed. DO PV = %.1f." % (t - start, pv))
                log_time += 10
            if t > end:
                break
            if pv > 90:
                break

        self.logger.info("Test finished. DO PV = %.1f after %d seconds." % (app.getdopv(), time() - start))

        self.logger.info("Ending batch")
        app.endbatch()
        return batch_name


class _dbgmeta(type):
    level = 0

    def __new__(mcs, name, bases, kwargs):
        from types import FunctionType

        def decorator(f):
            def wrapper(*args, **kwargs):
                nonlocal mcs
                print(mcs.level * " ", "Function called: ", f.__name__, sep='')
                mcs.level += 1
                rv = f(*args, **kwargs)
                mcs.level -= 1
                print(mcs.level * " ", "Function returned: ", f.__name__, sep='')
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
    def __init__(self, files=(), path='', savename="Compiled KLA Data"):

        self._tests = []
        for file in files:
            self.add_file(file)

        self._xl, self._wb, self._ws, self._cells = xlObjs()
        self._ws.Name = "Data"
        self._path = path or "C:\\Users\\Public\\Documents\\PBSSS\\KLA Testing\\"
        if not self._path.endswith("\\"):
            self._path += "\\"
        self._ln_chart = None
        self._linear_chart = None
        self._current_col = 1
        self._savename = savename

    def add_file(self, filename, name=None):
        t = KLAReport(name, None, None, filename)
        self._tests.append(t)

    def add_test(self, test):
        self._tests.append(test)

    def analyze_all(self):
        with HiddenXl(self._xl):
            self._init_linear_chart()
            self._init_ln_chart()
            for i, f in enumerate(self._tests, 1):
                print("Analyzing file #%d of %d" % (i, len(self._tests)))
                self.analyze_file(f.filename, f.name)
                print()

            self._linear_chart.Location(1, "Time v DOPV")
            self._ln_chart.Location(1, "Time v LN DOPV")

            for chart in (self._ln_chart, self._linear_chart):
                try:
                    AddTrendlines(chart)
                except:
                    print("Couldn't add trendlines")

            self.save()

    def save(self):
        self._wb.SaveAs(self._path + self._savename, AddToMru=True)

    def close(self):
        self._xl.Visible = True
        self._xl = self._wb = self._ws = self._cells = self._ln_chart = self._ln_chart = None

    def analyze_file(self, file, name=''):

        # identifying name for chart/test/series
        file = file.replace("/", "\\")
        print("Analyzing file:", file[file.rfind("\\") + 1:])

        if not name:
            try:
                mode, volume, ag, gas_flow = match(r"kla(\d*)-(\d*)-(\d*)-(\d*)", path_split(file)[1]).groups()
            except AttributeError:
                name = "KLA"
            else:
                if mode == '0':
                    unit = " RPM"
                else:
                    unit = "% Power"
                name = "KLA %sL %s%s %s mLPM" % (volume, ag, unit, gas_flow)

        print("Processing file.")
        xl_name = self.process_csv(file, name)
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

        # copy data to new ws
        with HiddenXl(xl):
            do_cell = cells.Find("DOPV(%)", cells(1, 1), SearchOrder=xlByRows)
            fleft = do_cell.Column
            fright = cells(2, fleft).End(xlToRight).Column
            fbottom = do_cell.End(xlDown).Row

            value = cells.Range(cells(1, fleft), cells(fbottom, fright)).Value
            trng = self._cells.Range(self._cells(2, self._current_col),
                                     self._cells(fbottom + 1, self._current_col + fright - fleft))
            trng.Value = value

            # column titles + identifying name
            self._cells(1, self._current_col).Value = series_name
            self._cells(2, self._current_col + 1).Value = "Elapsed Time"
            self._cells(2, self._current_col + 3).Value = "-LN(100-DOPV)"

            # add LN chart
            if self._ln_chart is None:
                self._init_ln_chart()
            chart = self._ln_chart
            xrng, yrng = chart_range_strs(self._current_col + 1, self._current_col + 3, 3, fbottom + 1, self._ws.Name)
            CreateDataSeries(chart, xrng, yrng, series_name)

            # add linear chart
            if self._linear_chart is None:
                self._init_linear_chart()
            chart = self._linear_chart
            xrng, yrng = chart_range_strs(self._current_col + 1, self._current_col + 2, 3, fbottom + 1, self._ws.Name)
            CreateDataSeries(chart, xrng, yrng, series_name)

        self._current_col += fright - fleft + 2

    def process_csv(self, file, chart_name="KLA"):
        """
        Analyzing data is ugly. Analyze 'file', where 'file' is a csv file
         corresponding to a batch data report with KLA data.
        """
        print("Opening new worksheet")
        xl, wb, ws, cells = xlObjs(file, visible=False)
        with HiddenXl(xl):
            # XXX what if cell not found?
            do_cell = cells.Find(What="DOPV(%)", After=cells(1, 1), SearchOrder=xlByRows)
            xcol = do_cell.Column + 1
            end_row = do_cell.End(xlDown).Row
            print("Performing data analysis")
            self._insert_time_col(ws, cells, xcol)
            self._insert_ln_col(ws, cells, xcol + 2)

            print("Creating data plot")
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

    def _insert_ln_col(self, ws, cells, col):

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

    def _insert_time_col(self, ws, cells, col):

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


class KLAReactorContext():
    def __init__(self, air_mfc_max, n2_mfc_max, o2_mfc_max,
                 co2_mfc_max, co2_min_flow, main_gas_max, vessel_capacity, is_mag):
        """
        @param air_mfc_max: air mfc max in L/min
        @param n2_mfc_max: n2 mfc max in L/min
        @param o2_mfc_max: o2 mfc max in L/min
        @param co2_mfc_max: co2 mfc max in L/min
        @param main_gas_max: main gas manual max (highest of above values)
        @param vessel_capacity: total capacity of vessel (eg, 4L for 3L, 100L for 80L...)

        POD class: parameters for reactor configuration
        """
        self.air_mfc_max = air_mfc_max
        self.n2_mfc_max = n2_mfc_max
        self.o2_mfc_max = o2_mfc_max
        self.co2_mfc_max = co2_mfc_max
        self.co2_min_flow = co2_min_flow
        self.main_gas_max = main_gas_max
        self.vessel_capacity = vessel_capacity
        self.is_mag = is_mag

    def __repr__(self):
        return "KLAReactorContext: %.1f LPM Air MFC, %.1f LPM N2 MFC, %.1f LPM CO2 MFC, %.1f LPM O2 MFC," \
               "%.1f LPM main gas max, %dL total vessel capacity, %s Drive" % (self.air_mfc_max, self.n2_mfc_max,
                                                                    self.co2_mfc_max, self.o2_mfc_max,
                                                                    self.main_gas_max, self.vessel_capacity, "Mag"
                                                                    if self.is_mag else "Air")


class KLATestContext():
    """
    Test parameters for the test itself.
    Includes filename info, etc.
    """
    def __init__(self, test_time, headspace_purge_factor, do_start_target, docroot=_docroot):
        self.test_time = test_time
        self.hs_purge_factor = headspace_purge_factor
        self.do_start_target = do_start_target
        self.docroot = docroot

    def generate_filename(self, name):
        """
        Generate filename.
        Default impl based on current date.
        Override for custom behavior if desired.
        """
        dirname = "%s%s%s\\" % (self.docroot, "kla",
                                datetime.now().strftime("%m-%d-%y"))
        makedirs(dirname, exist_ok=True)
        filename = dirname + name + ".csv"
        filename = unique_name(filename)
        return filename

    def __repr__(self):
        return "KLATestContext: %d min test time, %dx headspace purge, %d%% DO start target" % \
               (self.test_time, self.hs_purge_factor, self.do_start_target)


pbs_3L_ctx = KLAReactorContext(0.5, 0.5, 0.5, 0.3, 0.02, 0.5, 4, 1)
_default_r_ctx = pbs_3L_ctx
_default_t_ctx = KLATestContext(7, 5, 10)


class AirKLATestRunner():
    """
    Run a group of KLA tests on an air wheel reactor.
    """
    def __init__(self, ipv4, reactor_ctx=None, test_ctx=None):
        self.app = open_hello(ipv4)
        self.tests_to_run = []
        self.tests_run = []
        self.tests_skipped = []
        self.tests_pending = []
        self.ntests_run = 0

        if reactor_ctx is None:
            reactor_ctx = _default_r_ctx
        if test_ctx is None:
            test_ctx = _default_t_ctx

        self.reactor_ctx = reactor_ctx
        self.test_ctx = test_ctx

    def import_batch(self, batchname):
        self.app.login()
        b = self.app.getdatareport_bybatchname(batchname)
        filename = self.test_ctx.generate_filename(batchname)

        with open(filename, 'wb') as f:
            f.write(b)

        t = AirKLATest(self.app, 0, 0, 0, batchname, self.reactor_ctx, self.test_ctx)
        r = KLAReport(batchname, None, b, filename)
        t.report = r
        self.tests_run.append(t)

    def pickle_completed(self):
        pkl_file = self.test_ctx.docroot + "klapickle\\airklatestpikle.pkl"
        safe_pickle(self.tests_run, pkl_file)

    def add_test(self, test):
        """
        @type test: AirKLATest
        """
        self.tests_to_run.append(test)

    def create_test(self, main_sp, micro_sp, volume, name):
        # def create_test(a, b, c...)
        # t = AirKLATest(a, b, c...)
        # self.tests.append(t)
        t = AirKLATest(self.app, main_sp, micro_sp, volume, name, self.reactor_ctx, self.test_ctx)
        self.add_test(t)
        return t

    def skip_current_test(self):
        t = self.tests_pending.pop()
        self.tests_skipped.append(t)

    def run_once(self):
        self.ntests_run += 1
        t = self.tests_to_run.pop()
        print("Test #%d starting: %s" % (self.ntests_run, t.get_info()))
        self.tests_pending.append(t)
        try:
            t.run()
        except SkipTest as e:
            print(e.args)
            self.skip_current_test()
        except Exception:
            traceback.print_exc()
            self.skip_current_test()
        else:
            self.tests_pending.pop()
            self.tests_run.append(t)
            assert t.report

    def run_all(self):
        # run all tests. reverse list in the beginning,
        # then run 1 by 1 using .pop() to iterate in
        # correct order while removing from list.
        self.tests_to_run.reverse()
        while self.tests_to_run:
            self.run_once()


class AirKLATest():
    """
    Air KLA test.

    Requires hardware modification to configure tubing lines such that
    the test can be automated without requiring operator to switch tubing
    lines.

    Requirements for this class:
    * Air and N2 flow into main gas line
    * CO2 and O2 flow into micro gas line
    * Air and O2 flow compressed air
    * N2 and CO2 flow compressed nitrogen gas
    * PBS 2.0 software
    """

    def __init__(self, app, main_sp, micro_sp, volume, name,
                 reactor_ctx=None, test_ctx=None):
        """
        @param app: HelloApp
        @param main_sp: Main Gas (manual agitation) setpoint
        @param micro_sp: micro sparger (manual DO O2) setpoint
        @param volume: volume in reactor
        @param name: name to use for batch file.
        @param reactor_ctx: reactor context
        @type reactor_ctx: KLAReactorContext
        """
        self.name = name
        self.app = open_hello(app)
        self.main_sp = main_sp
        self.micro_sp = micro_sp
        self.volume = volume
        self.report = None

        if reactor_ctx is None:
            reactor_ctx = _default_r_ctx
        if test_ctx is None:
            test_ctx = _default_t_ctx

        if reactor_ctx.is_mag:
            self.set_gas = self.setmg
        else:
            self.set_gas = self.setag

        self.reactor_ctx = reactor_ctx
        self.test_ctx = test_ctx

        # Can be changed to logger.info, etc
        self.print = print

    def get_info(self):
        """
        @return: string describing the test
        """
        return '"%s" %.3fLPM %dmLPM %.2fL' % (self.name, self.main_sp, self.micro_sp, self.volume)

    __repr__ = get_info

    def run(self):

        self.print("Beginning setup")
        self.setup()

        self.print("Clearing headspace")
        self.clear_headspace()

        self.print("Running experiment")
        self.experiment()

        self.print("Post experiment cleanup")
        self.post_experiment()

        self.print("Experiment concluded")

    def _poll_do_setup(self, timeout):
        update_interval = 2
        end = timeout + _time()
        while True:
            do_pv = self.app.getdopv()
            if do_pv < self.test_ctx.do_start_target:
                self.print("")
                return True
            if _time() > end:
                self.print("")
                return False
            _sleep((end - _time()) % update_interval)
            self.print("\r                                               ", end='')
            self.print("\rDO PV: %.1f%%" % do_pv, end='')
        return True

    def _set_do_rampup(self):
        co2_flow = self.reactor_ctx.co2_min_flow
        n2_flow = co2_flow * 5
        total = co2_flow + n2_flow
        ph_pc = co2_flow / total * 100
        do_pc = n2_flow / total * 100
        self.app.setph(1, ph_pc, 0)
        self.app.setdo(1, do_pc, 0)
        self.set_gas(1, total)

    def setup(self):
        """
        Lower DO to < 10% using N2 from CO2 (micro)
        and N2 (main) gas lines.

        loop for 30 minutes or until DO PV < 10%
        IP00044 Rev A calls for lowering DO PV to < 20%,
        but we lower to 10% because we will be using the
        main gas line to purge headspace gas.

        The extra 10% helps compensate for increase in
        DO PV caused by air bubbles passing through the
        solution during the headspace purge.

        The poll/wait loop is performed in `_poll_do_setup`.
        This makes it a lot easier to use as it needs to be
        used twice- once with low CO2 flow (to simulate the
        DO rampup feature) and once with max flow.
        """
        self.app.login()

        # fastpath
        if self.app.getdopv() > self.test_ctx.do_start_target:

            self.print("Beginning DO PV bringdown.")
            self._set_do_rampup()
            if not self._poll_do_setup(15):

                ph_pc = self.reactor_ctx.co2_mfc_max / self.reactor_ctx.main_gas_max * 100
                do_pc = 100 - ph_pc

                self.app.setph(1, ph_pc, 0)  # 3L -> 0.3 LPM CO2 micro sparger
                self.app.setdo(1, do_pc, 0)  # 3L -> 0.2 LPM N2 main sparger
                self.set_gas(1, self.reactor_ctx.main_gas_max)

                if not self._poll_do_setup(60 * 30):
                    raise SkipTest("Setup timeout waiting for DO PV < %d%%" % self.test_ctx.do_start_target)

                self.print("")

        # post setup- all controllers off.
        self.app.login()
        self.app.setph(2, 0, 0)
        self.app.setdo(2, 0, 0)
        self.set_gas(2, 0)

    def clear_headspace(self):
        """
        Run "headspace" gas to pass headspace volume * 5 L of air.
        """
        headspace = self.reactor_ctx.vessel_capacity - self.volume
        t_min = headspace / self.reactor_ctx.main_gas_max * self.test_ctx.hs_purge_factor

        self.app.login()
        self.app.setph(2, 0, 0)
        self.app.setdo(2, 0, 0)
        self.set_gas(1, self.reactor_ctx.main_gas_max)

        now = _time()
        end = now + 60 * t_min
        while True:
            left = end - _time()
            left = max(left, 0)
            if left < 15:
                if left:
                    self.print("\r                                          ", end="")
                    self.print("\rHeadspace purge: %s seconds remain" % (int(end - _time())), end="")
                    _sleep(left)
                break
            else:
                _sleep(int(left) % 15)
                self.print("\r                                          ", end="")
                self.print("\rHeadspace purge: %s seconds remain" % (int(end - _time())), end="")
                _sleep(1)

        self.print("\nPurge Finished")
        self.app.login()
        self.set_gas(2, 0)

    def experiment(self):

        self.app.login()

        if self.app.batchrunning():
            self.app.endbatch()
        self.app.startbatch(self.name)

        self.app.setph(2, 0, 0)
        self.app.setdo(1, 0, self.micro_sp)
        self.set_gas(1, self.main_sp)

        end = _time() + self.test_ctx.test_time * 60
        update_interval = 15
        while True:
            left = max(end - _time(), 0)
            if left < update_interval:
                _sleep(left)
                break
            self.print("\r                                                          ", end="")
            self.print("\rExperiment running: %s seconds left. DO PV: %.1f%%" %
                       (int(end - _time()), self.app.getdopv()), end="")
            _sleep(left % 15)

        self.print("")
        self.app.login()
        self.app.endbatch()

        self.set_gas(2, 0)
        self.app.setdo(2, 0)

    def post_experiment(self):

        self.app.login()
        b = self.app.getdatareport_bybatchname(self.name)

        filename = self.test_ctx.generate_filename(self.name)
        with open(filename, 'wb') as f:
            f.write(b)

        self.report = KLAReport(self.name, None, b, filename)

    def setmg(self, mode, val):
        self.app.setmg(mode, val)

    def setag(self, mode, val):
        self.app.setag(mode, val)


def __test_analyze_kla():

    test_dir = "C:\\Users\\Public\\Documents\\PBSSS\\KLA Testing\\PBS 3 mech wheel\\test\\"
    file = test_dir + "kla0-10-200 id-35 27-10-14.csv"
    KLAAnalyzer((file,)).analyze_all()


def __test_airkla():

    rc = KLAReactorContext(0.5, 0.5, 0.5, 0.3, 0.02, 0.5, 4, 1)
    tc = KLATestContext(7, 5, 5)

    r = AirKLATestRunner("71.189.82.196:6", rc, tc)
    r.test_ctx.hs_purge_factor = 0.5
    r.test_ctx.test_time = 1
    r.test_ctx.do_start_target = 15

    r.create_test(0.051, 60, 3, "kla t11 id27")
    r.create_test(0.153, 60, 3, "kla t55 id55")
    return r


if __name__ == '__main__':
    # test = MechKLATest('192.168.1.6')
    # test.setup()
    r = __test_airkla()
    t = r.tests_to_run[0]
    t.setup()

