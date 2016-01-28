"""

Created by: Nathan Starkweather
Created on: 10/21/2014
Created in: PyCharm Community Edition


"""
from pbslib import pretty_date
from officelib.const import xlToRight, xlByRows, xlDown, xlXYScatter, xlOpenXMLWorkbook
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
    from hello import HelloError, HelloApp, open_hello, TrueError
except ImportError:
    from hello.hello import HelloError, HelloApp, open_hello, TrueError
    
from pysrc.logger import BuiltinLogger


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


class _SimpleAddress():
    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.address = cellStr(row, col)
        self.abs_address = cellStr(row, col, 1, 1)


class _MakeNamedRanges():
    """ The old "_make_named_ranges" function in KLAAnalyzer
    was responsible for doing a lot of work and in the process
    calculated a lot of important values.
    
    This class will attempt to take that functionality and
    encapsulate it, to make the state more accessible to
    KLAAnalyzer for re-use, and more flexible to use. 
    
    Storing all variables in state will also allow the function to
    be broken down a bit to spread out the individual pieces.
    
    Make named ranges and insert cell values in two column
        matrix in the following format:

        [m_col_1]       [m_col_2]
        x_col           y_col
        start_row
        end_row
        x_range         y_range
        "m"             "b"
        m_form          b_form

    This is done to enable dynamic named ranges in excel
    controlled by numerical entries in the spreadsheet
    itself.
    """

    def __init__(self, wb, ws, cells, start_row, end_row, date_col):
        self.wb = wb
        self.ws = ws
        self.cells = cells
        self.start_row = start_row
        self.end_row = end_row
        self.date_col = date_col
        self.m_col_1 = date_col + 4
        self.m_col_2 = date_col + 5

        self.address_matrix = []
        for col in range(2):
            col_list = []
            self.address_matrix.append(col_list)
            for row in range(7):
                col_list.append(_SimpleAddress(row + start_row, col + self.m_col_1))

    def cell_addy(self, row, col, abs=False):
        addy = self.address_matrix[col - self.m_col_1][row - self.start_row]
        if abs:
            return addy.abs_address
        else:
            return addy.address
        
    def close(self):
        """ Release references """
        self.wb = self.ws = self.cells = None

    def get_ranges(self):
        return self._make_named_ranges(self.wb, self.ws, self.cells, self.start_row, self.end_row, self.date_col)

    def _make_named_ranges(self, wb, ws, cells, start_row, end_row, date_col):

        # address range strings for first cell in x, f(x), and f(-ln(100-x)) columns
        x_col_start_cell = cellStr(start_row, date_col + 1, 1, 1)
        lin_col_start_cell = cellStr(start_row, date_col + 2, 1, 1)
        ln_col_start_cell = cellStr(start_row, date_col + 3, 1, 1)

        # address range strings for cells as in docstring matrix
        x_col_str = cellStr(2, self.m_col_1, 1, 1)
        y_col_str = cellStr(2, self.m_col_2, 1, 1)
        start_row_str = cellStr(3, self.m_col_1, 1, 1)
        end_row_str = cellStr(4, self.m_col_1, 1, 1)

        # cell formulas for "x_range" and "y_range" in docstring matrix
        #
        x_range = '=%s&%s&":"&%s&%s' % (x_col_str, start_row_str,
                                        x_col_str, end_row_str)
        y_range = '=%s&%s&":"&%s&%s' % (y_col_str, start_row_str,
                                        y_col_str, end_row_str)

        # column letters
        cells(2, self.m_col_1).Value = cellStr(1, date_col + 1).replace("1", "")
        cells(2, self.m_col_2).Value = cellStr(1, date_col + 3).replace("1", "")

        # start and end row for dynamic range
        cells(3, self.m_col_1).Value = start_row
        cells(4, self.m_col_1).Value = end_row

        # x and y ranges
        cells(5, self.m_col_1).Value = x_range
        cells(5, self.m_col_2).Value = y_range
        ws.Columns(self.m_col_1).NumberFormat = "General"

        # m and b
        cells(6, self.m_col_1).Value = "m"
        cells(6, self.m_col_2).Value = "b"
        cells(7, self.m_col_1).Value = "=index(linest(indirect(%s), indirect(%s)), 1)" \
                                       % (cells(5, self.m_col_1).Address, cells(5, self.m_col_2).Address)
        cells(7, self.m_col_2).Value = "=index(linest(indirect(%s), indirect(%s)), 2)" \
                                       % (cells(5, self.m_col_1).Address, cells(5, self.m_col_2).Address)

        # build name & formula for named range. this is obnoxious.
        # for the sake of readability, I have named them bob and fred.
        # bob = x named range, fred = y named range
        name_x = "__%d_x_%s"
        name_y = "__%d_y_%s"
        bob_name_ln = name_x % (date_col, "ln")
        fred_name_ln = name_y % (date_col, "ln")
        bob_name_lin = name_x % (date_col, "lin")
        fred_name_lin = name_y % (date_col, "lin")

        book_name = wb.Name
        sheet_name = "'%s'!" % ws.Name

        # offset(ref, rows, cols)
        #
        # Dynamic named ranges worth with the offset formula,
        # but not with the indirect formula (which would make this
        # much easier to read).
        #
        # This formula translates the x_col, y_col, start row, and end_row
        # into ranges which correspond to the formulas listed in
        # x_range and y_range.
        named_range_formula = "=offset(%s%s,%s%s-%d,0):" \
                              "offset(%s%s,%s%s-%d,0)"

        bob_formula_ln = named_range_formula % (sheet_name, x_col_start_cell,
                                                sheet_name, start_row_str, start_row,
                                                sheet_name, x_col_start_cell,
                                                sheet_name, end_row_str, start_row)

        fred_formula_ln = named_range_formula % (sheet_name, ln_col_start_cell,
                                                 sheet_name, start_row_str, start_row,
                                                 sheet_name, ln_col_start_cell,
                                                 sheet_name, end_row_str, start_row)

        # x column is the same for both formulas
        bob_formula_lin = bob_formula_ln

        fred_formula_lin = named_range_formula % (sheet_name, lin_col_start_cell,
                                                  sheet_name, start_row_str, start_row,
                                                  sheet_name, lin_col_start_cell,
                                                  sheet_name, end_row_str, start_row)

        add_name = wb.Names.Add
        add_name(bob_name_ln, bob_formula_ln)
        add_name(fred_name_ln, fred_formula_ln)
        add_name(bob_name_lin, bob_formula_lin)
        add_name(fred_name_lin, fred_formula_lin)

        # these are exported for use in chart data series address strings
        chart_form = "='%s'!%%s" % book_name
        bob_chart_ln_form = chart_form % bob_name_ln
        fred_chart_ln_form = chart_form % fred_name_ln
        bob_chart_lin_form = chart_form % bob_name_lin
        fred_chart_lin_form = chart_form % fred_name_lin

        return bob_chart_ln_form, fred_chart_ln_form, bob_chart_lin_form, \
               fred_chart_lin_form


class KLAAnalyzer():
    def __init__(self, files=(), savepath='', savename="Compiled KLA Data"):

        self._tests = []
        files = files or ()
        for file in files:
            self.add_file(file)

        self._xl, self._wb, self._ws, self._cells = xlObjs()
        self._ws.Name = "Data"
        self._path = savepath or "C:\\Users\\Public\\Documents\\PBSSS\\KLA Testing\\" + pretty_date() + "\\"
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
        makedirs(self._path, exist_ok=True)
        with HiddenXl(self._xl):
            self._init_linear_chart()
            self._init_ln_chart()
            for i, f in enumerate(self._tests, 1):
                print("Analyzing file #%d of %d" % (i, len(self._tests)))
                self.analyze_file(f.filename, f.name)
                print()

            for chart in (self._ln_chart, self._linear_chart):
                try:
                    AddTrendlines(chart)
                except:
                    print("Couldn't add trendlines")

            self._linear_chart.Location(1, "Time v DOPV")
            self._ln_chart.Location(1, "Time v LN DOPV")

        self.save()

    def save(self):
        try:
            self._wb.SaveAs(self._path + self._savename, AddToMru=True)
        except:
            import traceback
            traceback.print_exc()

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
        chart = CreateChart(self._ws, xlXYScatter)
        FormatChart(chart, None, "KLA Data (compiled)", "Time(hr)", "DOPV(%)")
        self._linear_chart = chart

    def _init_ln_chart(self):
        chart = CreateChart(self._ws, xlXYScatter)
        FormatChart(chart, None, "KLA Data (compiled, -LN(100-DOPV))", "Time(hr)", "-LN(100-DOPV)")
        self._ln_chart = chart

    def add_to_compiled(self, file, series_name):
        xl, wb, ws, cells = xlObjs(file, visible=False)

        # copy data to new ws
        with HiddenXl(xl, True):
            do_cell = cells.Find("DOPV(%)", cells(1, 1), SearchOrder=xlByRows)
            fleft = do_cell.Column
            fright = fleft + 3
            fbottom = do_cell.End(xlDown).Row

            value = cells.Range(cells(1, fleft), cells(fbottom, fright)).Value
            trng = self._cells.Range(self._cells(2, self._current_col),
                                     self._cells(fbottom + 1, self._current_col + fright - fleft))
            trng.Value = value

            # column titles + identifying name
            self._cells(1, self._current_col).Value = series_name
            self._cells(2, self._current_col + 1).Value = "Elapsed Time"
            self._cells(2, self._current_col + 3).Value = "-LN(100-DOPV)"

            ln_x, ln_y, lin_x, lin_y = _MakeNamedRanges(self._wb, self._ws, self._cells, 3, fbottom + 1,
                                                               self._current_col).get_ranges()
            
            series_name = ("='%s'!" % self._ws.Name) + cellStr(1, self._current_col)

            # add LN chart
            if self._ln_chart is None:
                self._init_ln_chart()
            chart = self._ln_chart
            CreateDataSeries(chart, ln_x, ln_y, series_name)

            # add linear chart
            if self._linear_chart is None:
                self._init_linear_chart()
            chart = self._linear_chart
            CreateDataSeries(chart, lin_x, lin_y, series_name)

        self._current_col += fright - fleft + 2 + 2  # +2 space, + 2 regression columns

    def process_csv(self, file, chart_name="KLA"):
        """
        Analyzing data is ugly. Analyze 'file', where 'file' is a csv file
         corresponding to a batch data report with KLA data.
        """
        print("Opening new worksheet")
        xl, wb, ws, cells = xlObjs(file, visible=False)
        with HiddenXl(xl, True):
            # XXX what if cell not found?
            do_cell = cells.Find(What="DOPV(%)", After=cells(1, 1), SearchOrder=xlByRows)
            xcol = do_cell.Column + 1
            end_row = do_cell.End(xlDown).Row
            print("Performing data analysis")
            self._insert_time_col(ws, cells, xcol)
            self._insert_ln_col(ws, cells, xcol + 2)

            print("Creating data plot")

            # XXX possible in one call?
            ws.Columns(xcol + 3).Insert(Shift=xlToRight)
            ws.Columns(xcol + 3).Insert(Shift=xlToRight)

            ln_x, ln_y, lin_x, lin_y = _MakeNamedRanges(wb, ws, cells, 2, end_row, xcol - 1).get_ranges()

            # ln v time for specific chart
            chart = CreateChart(ws, xlXYScatter)
            CreateDataSeries(chart, ln_x, ln_y)
            FormatChart(chart, None, chart_name + "-LN(100-DOPV)", "Time(hour)", "-LN(DO PV (%))", True, False)

            # do v time
            chart2 = CreateChart(ws, xlXYScatter)
            CreateDataSeries(chart2, lin_x, lin_y)
            FormatChart(chart2, None, chart_name + "DO PV", "Time(hour)", "DO (%)", True, False)

            # uncomment to move to move chart to new sheet
            # xlLocationAsNewSheet = 1
            # chart.Location(1)

            save_name = file.replace(file[file.rfind("."):], '.xlsx')

            # uncomment to save in raw data  folder
            # wb.SaveAs(save_name, AddToMru=False)
            
            wb.SaveAs(self._path + path_split(save_name)[1], AddToMru=False, FileFormat=xlOpenXMLWorkbook)

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
                 co2_mfc_max, co2_min_flow, main_gas_max, vessel_capacity, is_mag, o2_min_flow_time,
                 o2_tubing_volume, o2_mfc_min):
        """

        @param air_mfc_max: air mfc max in L/min
        @param n2_mfc_max: n2 mfc max in L/min
        @param o2_mfc_max: o2 mfc max in L/min
        @param co2_mfc_max: co2 mfc max in L/min
        @param co2_min_flow: co2 mfc min in L/min
        @param main_gas_max: main gas manual max (highest of above values)
        @param vessel_capacity: total capacity of vessel (eg, 4L for 3L, 100L for 80L...)
        @param is_mag: 1 if doing air test on mag drive unit, 0 if air on air drive.
        @param o2_min_flow_time: time to wait for o2 to ramp up, in seconds

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
        self.o2_min_flow_time = o2_min_flow_time
        self.o2_tubing_volume = o2_tubing_volume
        self.o2_mfc_min = o2_mfc_min

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
    def __init__(self, test_time, headspace_purge_factor, do_start_target, savedir=_docroot):
        self.test_time = test_time
        self.hs_purge_factor = headspace_purge_factor
        self.do_start_target = do_start_target
        self.savedir = savedir

    def generate_filename(self, name):
        """
        Generate filename.
        Default impl based on current date.
        Override for custom behavior if desired.
        """
        dirname = "%s%s%s\\" % (self.savedir, "kla",
                                datetime.now().strftime("%m-%d-%y"))
        makedirs(dirname, exist_ok=True)
        filename = dirname + name + ".csv"
        filename = unique_name(filename)
        return filename

    def __repr__(self):
        return "KLATestContext: %d min test time, %dx headspace purge, %d%% DO start target" % \
               (self.test_time, self.hs_purge_factor, self.do_start_target)


pbs_3L_ctx = KLAReactorContext(0.5, 0.5, 0.5, 0.3, 0.02, 0.5, 4, 1, 30, 30, 20)
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

        self.logger = BuiltinLogger(self.__class__.__name__ + datetime.now().strftime("%m-%d-%Y %H-%M"))
        self.logger.handlers.pop(0)  # XXX bad practice

        if reactor_ctx is None:
            reactor_ctx = _default_r_ctx
        if test_ctx is None:
            test_ctx = _default_t_ctx

        self.reactor_ctx = reactor_ctx
        self.test_ctx = test_ctx

    def print(self, *args, **kwargs):
        print(*args, **kwargs)

        msg = kwargs.get("sep", " ").join(args).replace("\r", "")
        if msg:
            self.logger.info(msg)

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
        pkl_file = self.test_ctx.savedir + "klapickle\\airklatestpikle.pkl"
        safe_pickle(self.tests_run, pkl_file)

    def add_test(self, test):
        """
        @type test: AirKLATest
        """
        test.print = self.print
        self.tests_to_run.append(test)

    def create_test(self, main_sp, micro_sp, volume, name):
        t = AirKLATest(self.app, main_sp, micro_sp, volume, name, self.reactor_ctx, self.test_ctx)
        self.add_test(t)
        return t

    def skip_current_test(self):
        t = self.tests_pending.pop()
        self.tests_skipped.append(t)

        self.app.login()
        if self.reactor_ctx.is_mag:
            self.app.setmg(2, 0)
        else:
            self.app.setag(2, 0)
        self.app.setph(2, 0, 0)
        self.app.setdo(2, 0, 0)
        self.app.logout()

    def run_once(self):
        self.ntests_run += 1
        t = self.tests_to_run.pop()
        self.print("-------------------------------------------")
        self.print("Test #%d starting: %s" % (self.ntests_run, t.get_info()))
        self.tests_pending.append(t)
        try:
            t.run()
        except SkipTest as e:
            self.print(e.args)
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

        if self.tests_skipped:
            self.print("------------------------")
            self.print("Skipped tests:")
            for t in self.tests_skipped:
                self.print(t.get_info())


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
                return True
            if _time() > end:
                return False
            _sleep((end - _time()) % update_interval)
            self.print("\rDO PV: %.1f%% / %.1f%%                    " % (do_pv, self.test_ctx.do_start_target), end='')
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
        
    def _verify(self, used_ph_m, used_ph_sp,
                      used_do_m, used_do_sp,
                      used_gas_m, used_gas_sp):

        mv = self.app.gpmv()

        ph = mv['ph']
        ph_m = ph['mode']
        ph_sp = ph['manDown']

        do = mv['do']
        do_m = do['mode']
        do_sp = do['manUp']

        if self.reactor_ctx.is_mag:
            gas = mv['maingas']
        else:
            gas = mv['agitation']

        gas_m = gas['mode']
        gas_sp = gas['man']

        return all((ph_m == used_ph_m, ph_sp == used_ph_sp,
                    do_m == used_do_m, do_sp == used_do_sp,
                    gas_m == used_gas_m, gas_sp == used_gas_sp))
            
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
                    self.print("")
                    raise SkipTest("Setup timeout waiting for DO PV < %d%%" % self.test_ctx.do_start_target)

                self.print("")

        # subtlety in this test setup- at this point, main and micro
        # gas lines are both full of nitrogen. The main gas line is
        # purged during headspace purge, but the N2 from micro
        # gas line will come out during experiment and cause problems.
        # so we have to clear that gas and then finish the bringdown with
        # main gas N2 only.
        self.app.login()
        o2_purge_time = self.reactor_ctx.o2_tubing_volume / self.reactor_ctx.o2_mfc_min
        self.app.setdo(1, 0, self.reactor_ctx.o2_mfc_min)
        self.print("Beginning micro gas line purge %d second sleep" % int(o2_purge_time * 60))
        self.app.logout()
        _sleep(o2_purge_time * 60)

        self.app.login()
        self.app.setdo(2, 0, 0)
        self.app.logout()
        self._poll_do_setup(60 * 10)

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

    def _begin_batch(self, max_tries=20):
        """
        Subroutine to ensure that batch is started
        some issues have arisen with server calls
        not being accepted.

        Issue #1: startbatch not accepted.
        Issue #2: ODBC database driver error or w/e
        """
        n = 1
        while True:
            self.print("\rAttempting to begin batch: Attempt #%d of %d              "
                       % (n, max_tries))
            try:
                self.app.startbatch(self.name)
            except HelloError:  # odbc error
                pass
            _sleep(1)
            bn = self.app.getDORAValues()['Batch']
            if bn.lower() == self.name.lower():
                return
            if n > max_tries:
                raise SkipTest("Failed to start batch")
            n += 1

    def experiment(self):

        self.app.login()

        if self.app.batchrunning():
            self.app.endbatch()

        self.app.setph(2, 0, 0)
        self.app.setdo(1, 0, self.micro_sp)
        self.set_gas(1, self.main_sp)

        self.print("Sleeping %d seconds for O2 rampup" % self.reactor_ctx.o2_min_flow_time)
        _sleep(self.reactor_ctx.o2_min_flow_time)

        self._begin_batch()
        self.app.logout()

        end = _time() + self.test_ctx.test_time * 60
        update_interval = 5
        dopv = 0.0
        while True:
            left = max(end - _time(), 0)
            if left < update_interval:
                _sleep(left)
                assert _time() >= end
                break
            self.print("\r                                                          ", end="")
            try:
                dopv = self.app.getdopv()
            except:
                pass
            self.print("\rExperiment running: %s seconds left. DO PV: %.1f%%" %
                       (int(end - _time() + 1), dopv), end="")
            _sleep(left % update_interval)

        self.print("")
        self.app.login()

        self.set_gas(2, 0)
        self.app.setdo(2, 0)
        self.app.endbatch()

    def _try_getreport(self, n, max_tries=20):
        batch = None  # pycharm
        while True:
            self.app.login()
            self.print("\rAttempting to download report: Attempt #%d of %d              "
                       % (n, max_tries))
            try:
                batch = self.app.getdatareport_bybatchname(self.name)
            except TrueError:
                if n > max_tries:
                    raise
                try:
                    self.app.logout()
                except HelloError:
                    pass
                self.app.reconnect()
                n += 1
            else:
                break
        return batch

    def post_experiment(self):

        n = 1
        max_tries = 20
        b = self._try_getreport(n, max_tries)

        filename = self.test_ctx.generate_filename(self.name)
        with open(filename, 'wb') as f:
            f.write(b)

        self.report = KLAReport(self.name, None, b, filename)

    def setmg(self, mode, val):
        self.app.setmg(mode, val)

    def setag(self, mode, val):
        self.app.setag(mode, val)


def __test_analyze_kla():

    import subprocess
    subprocess.call("tskill.exe excel")
    test_dir = "C:\\Users\\Public\\Documents\\PBSSS\\KLA Testing\\PBS 3 mech wheel\\test\\"
    file = test_dir + "kla0-10-200 id-35 27-10-14.csv"
    test_save_dir = "C:\\.replcache\\__test_analyze_kla\\"

    import shutil
    shutil.rmtree(test_save_dir)

    KLAAnalyzer((file,), test_save_dir).analyze_all()


def __test_airkla():

    rc = KLAReactorContext(0.5, 0.5, 0.5, 0.3, 0.02, 0.5, 4, 1, 30, 30, 20)
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
    # r = __test_airkla()
    # t = r.tests_to_run[0]
    # t.setup()
    __test_analyze_kla()
    # pass

