"""

Created by: Nathan Starkweather
Created on: 11/19/2015
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'


from officelib.xllib import xlcom, xladdress
from officelib import const
from hello.hello import HelloApp
from hello.logger import BuiltinLogger, logging

import tempfile
import os
import math

###################
# Utility Functions
###################


def _extract_cell_data(cells, top_left, bottom_right):
    alldata = cells.Range(top_left, bottom_right).Value
    return list(zip(*alldata))

def _ave(o):
    return sum(o) / len(o)

def _get_filename(path):
    return os.path.splitext(os.path.basename(path))[0]

############
# Exceptions
############


class MixingTimeAnalysisError(Exception):
    pass

#########
# Classes
#########


class CompiledMixingSaveAsInfo():
    def __init__(self, path):
        self.path = os.path.normpath(path)
        if not os.path.exists(path):
            os.makedirs(path)

    def save_mt(self, mt):
        filename = os.path.join(self.path, mt.name) + ".xlsx"
        mt.wb.SaveAs(Filename=filename, FileFormat=const.xlOpenXMLWorkbook)

    def save_compiled(self, ct):
        filename = os.path.join(self.path, ct.name) + ".xlsx"
        ct.wb.SaveAs(filename)


class CompiledMixingTime():
    """
    Compiled collection of mixing time tests. Contains a list
     of tests, and adds data to a spreadsheet.

     Intended to be the primary entry point. Uses a BuiltinLogger
     passed on to all child tests created through its interface.
    """
    def __init__(self, name=None, xl=None, wb=None, logger=None, saveas_info=None):

        if xl or wb:
            if xl:
                wb = xl.Workbooks.Add()
            elif wb:
                xl = wb.Application
        else:
            xl, wb = xlcom.xlBook2()

        self.xl = xl
        self.wb = wb
        self.ws = wb.Worksheets(1)
        self.init_ws()
        self.name = name or "Compiled Data"
        self.logger = logger or BuiltinLogger(self.__class__.__name__, logging.INFO)
        self.tests = []
        self.compiled_tests = 0

        self.saveas_info = saveas_info or CompiledMixingSaveAsInfo("C:/.replcache/mixing test/")

    def init_ws(self):
        self.ws.Cells(2, 21).Value = "Name"
        self.ws.Cells(2, 22).Value = "T95"
        self.ws.Cells(2, 23).Value = "stdev"

    def sort_tests(self, key=lambda mt: mt.name[-3:]):
        self.tests.sort(key=key)

    def analyze_all(self):
        with xlcom.HiddenXl(self.xl, True):
            self.logger.info("Running analysis on %d tests.", len(self.tests))
            for mt in self.tests:
                mt.run_analysis()
                self.add_to_compiled(mt)
                self.save_test(mt)
        self.saveas_info.save_compiled(self)

    def save_test(self, mt):
        self.saveas_info.save_mt(mt)

    def add_csv(self, csv):
        mt = self._create_test_from_csv(csv)
        self.add_test(mt)
        return mt

    def add_frombatchname(self, ipv4, batch_name):
        mt = MixingTimeTest.from_batchname(ipv4, batch_name, None, self.logger)
        self.add_test(mt)
        return mt

    def add_batchnames(self, ipv4, batch_names):
        with xlcom.HiddenXl(self.xl, True):
            app = HelloApp(ipv4)
            app.login()
            batches = app.getBatches()
            for name in batch_names:
                id = batches.getbatchid(name)
                report = app.getdatareport_bybatchid(id)
                mt = MixingTimeTest.from_bytes(report, name, self.logger)
                self.add_test(mt)

    def add_test(self, test):
        self.tests.append(test)

    def _create_test_from_csv(self, file):
        return MixingTimeTest.from_csv(file, None, self.logger)

    def from_csv_list(self, files):
        for file in files:
            self.add_csv(file)

    def _add_chart_to_compiled(self, mixing_test):
        self.logger.debug("Adding test to compiled data worksheet")
        # fixme: move to config area(?)
        charts_per_row = 3
        chart_left_start = 30
        chart_top_start = 30
        chart_left_padding = 5
        chart_top_padding = 5
        mt_ws = mixing_test.ws
        mt_chart_ob = mt_ws.ChartObjects(1)
        chart = mt_chart_ob.Chart
        chart.ChartArea.Copy()
        self.ws.Paste()
        chart_objs = self.ws.ChartObjects()
        chart_count = chart_objs.Count
        chart_obj = chart_objs(chart_count)
        chart_width = mt_chart_ob.Width
        chart_height = mt_chart_ob.Height
        chart_count -= 1
        chart_left = (chart_count % charts_per_row) * chart_width + \
                     (chart_count % charts_per_row) * chart_left_padding + chart_left_start
        chart_top = (chart_count // charts_per_row) * chart_height + \
                    (chart_count // charts_per_row) * chart_top_padding + chart_top_start
        chart_obj.Height = chart_height
        chart_obj.Width = chart_width
        chart_obj.Left = chart_left
        chart_obj.Top = chart_top
        xlcom.FormatChart(chart_obj.Chart, None, mixing_test.name)

    def add_to_compiled(self, mixing_test):

        self._add_chart_to_compiled(mixing_test)

        cells = self.ws.Cells
        row = self.compiled_tests + 3 + self.compiled_tests // 3
        cells(row, 21).Value = mixing_test.name
        cells(row, 22).Value = mixing_test.t95
        cells.Columns(21).AutoFit()

        self.compiled_tests += 1


class MixingTimeTest():
    """
    Represents an individual mixing time test. Opens raw batch file
    and performs analysis.

    Intended to be instantized by above CompiledMixingTime. Can
    be used directly for individual tests or customization.
    """
    def __init__(self, name=None, xl=None, wb=None, logger=None, conductivity_var="phARaw"):
        self.logger = logger or BuiltinLogger(self.__class__.__name__)
        self.xl = xl
        self.wb = wb
        self.ws = wb.Worksheets(1)
        self.name = name

        self.logger.debug("New Test with name %s", name if name else "<no name>")

        if name:
            self.ws.Name = name

        self.cv = conductivity_var

    @classmethod
    def from_csv(cls, csv, name=None, logger=None):
        """
        @param csv: filename of csv file
        @param logger: Logger

        Instantize class from filename of raw batch file.
        Enter function at IP00043 Rev A 7.4.2
        """
        xl, wb = xlcom.xlBook2(csv)
        if name is None:
            name = _get_filename(csv)
        return cls(name, xl, wb, logger)

    @classmethod
    def from_bytes(cls, report, name=None, logger=None):
        with tempfile.NamedTemporaryFile("wb", suffix=".csv", delete=False) as t:
            t.write(report)
        self = cls.from_csv(t.name, name, logger)
        return self

    @classmethod
    def from_batchname(cls, ipv4, batch_name, name=None, logger=None):
        """
        @param ipv4: IP address of bioreactor
        @param batch_name: batch name of test batch
        @param logger: Logger

        Enter function at IP00043 Rev A 7.4.1
        """
        app = HelloApp(ipv4)
        app.login()
        r = app.getdatareport_bybatchname(batch_name)

        if name is None:
            name = batch_name

        return cls.from_bytes(r, name, logger)

    def _find_logger_ts_1k(self, cells):
        self.logger.debug("Searching for logger column: \"%s\"", self.cv)
        logger_col = cells.Find(What="LoggerMaxLogInterval(ms)",
                                After=cells(1, 1), SearchOrder=const.xlByRows)
        logger_col_values = cells.Columns(logger_col.Column + 1)
        self.logger.debug("Searching for first instance of \"1000\"")
        first_1k = logger_col_values.Find(What="1000", SearchOrder=const.xlByColumns)
        logger_timestamp = cells(first_1k.Row, logger_col.Column).Value
        self.logger.debug("Found logger timestamp: %s", logger_timestamp)
        return logger_timestamp

    def _add_cond_et_col(self, cells, logger_timestamp):
        self.logger.debug("Creating elapsed time column.")
        cc = cells.Find(What=self.cv, After=cells(1, 1), SearchOrder=const.xlByRows)
        cc_col = cc.Column
        cc_end_row = cc.End(const.xlDown).Row
        self.logger.debug("Extracting conductivity data")
        cond_data = _extract_cell_data(cells, cc, cells(cc_end_row, cc_col + 1))
        ts_data = cond_data[0][1:]
        for row, data in enumerate(ts_data, 2):
            if data > logger_timestamp:
                break
        else:
            raise MixingTimeAnalysisError("Failed to find conductivity start timestamp.")
        self.logger.debug("Found data. Generating Elapsed Time column")
        et_formulas = self._generate_et_formulas(row, cc_col, len(ts_data) + 1)
        cells.Columns(cc_col + 1).Insert()
        et_col = cells.Columns(cc_col + 1)
        cells.Range(et_col.Cells(row, 1), et_col.Cells(cc_end_row, 1)).Value = et_formulas
        et_col.NumberFormat = "0.0"
        et_col.Cells(1, 1).Value = "Elapsed Time (sec)"
        self.logger.debug("Elapsed Time column created.")
        return row, et_col, cc_end_row, cond_data

    def _add_raw_chart(self, cc_end_row, et_cc, first_data_row, ws):
        self.logger.debug("Creating chart of conductivity vs. time")
        chart = xlcom.CreateChart(ws)
        xlcom.FormatChart(chart, None, "Time vs. Raw Voltage",
                          "Time (sec)", self.cv, False, False)
        x_rng, y_rng = xladdress.chart_range_strs(et_cc, et_cc + 1,
                                                  first_data_row, cc_end_row, ws.Name)
        xlcom.CreateDataSeries(chart, x_rng, y_rng)
        return chart

    def _calc_last_80_forms(self, cc_end_row, cond_data, et_cc):
        self.logger.debug("Finding average of last 80 seconds.")
        ts_data = cond_data[0]
        end = len(ts_data) - 1
        last_pt = ts_data[-1]
        for i in range(end, -1, -1):
            if (last_pt - ts_data[i]).total_seconds() >= 80:
                i += 1  # back up
                break
        else:
            raise MixingTimeAnalysisError("Failed to find last 80 sec of data")
        first_pv_cell = (i + 1, et_cc + 1)
        last_pv_cell = (cc_end_row, et_cc + 1)
        ave_last_80 = "=average(%s:%s)" % (xladdress.cellStr(*first_pv_cell),
                                           xladdress.cellStr(*last_pv_cell))
        return ave_last_80

    def _find_pv95(self, cells, cond_data, et_cc):
        pc05 = cells(2, et_cc + 5).Value2
        cf = cells(2, et_cc + 4).Value2
        c95_min = cf - pc05
        c95_max = cf + pc05
        self.logger.debug("Searching for %s < x < %s", c95_min, c95_max)

        # search for first data point not within 5% of final
        # assume that data is sane, and flattens out over time
        # and doesn't have weird spikes near the end
        # and also isn't completely flat.

        cond_pvs = cond_data[1]
        last = len(cond_pvs) - 1
        for i in range(last, 0, -1):
            data = cond_pvs[i]
            if not c95_min <= data <= c95_max:
                i += 2  # +1 backup, +1 for 1-based row index
                if i > last:
                    i = last + 1
                break
        else:
            # is this even possible?
            raise MixingTimeAnalysisError("Failed to find point within 5% of final")
        cells(i, et_cc + 2).Value = "**pv95"
        return i

    def run_analysis(self):
        """
         XXX This analysis routine assumes data collected using the batch
             file method detailed in IP00043!
        """

        # Initialize
        self.logger.info("Beginning analysis on: %s", self.wb.Name)
        ws = self.ws
        cells = ws.Cells

        # 7.4.3 - Find first logger max log interval timestamp
        logger_timestamp = self._find_logger_ts_1k(cells)

        # 7.4.3 - Elapsed Time column for conductivity
        first_data_row, et_col, cc_end_row, cond_data = self._add_cond_et_col(cells, logger_timestamp)
        et_cc = et_col.Column

        # 7.4.4 - Graph time vs conductivity pv
        chart = self._add_raw_chart(cc_end_row, et_cc, first_data_row, ws)

        # 7.4.5 - Add initial conductivity, final ave conductivity over 80 sec
        free_col = cells.Columns(et_cc + 3)
        for _ in range(5):
            free_col.Insert()

        # 7.4.5.1 - Conductivity at t = 0 + header
        cells(1, et_cc + 3).Value = "Conductivity (T=0)"
        cells(2, et_cc + 3).Value = "=" + xladdress.cellStr(first_data_row,
                                                            et_cc + 1)
        cells.Columns(et_cc + 3).AutoFit()

        # 7.4.5.2 - final conductivity last 80 sec of batch
        ave_last_80 = self._calc_last_80_forms(cc_end_row, cond_data, et_cc)
        cells(1, et_cc + 4).Value = "Average last 80 sec"
        cells(2, et_cc + 4).Value = ave_last_80
        cells.Columns(et_cc + 4).AutoFit()

        # 7.4.5.3 - calculate 5% of final - initial conductivity
        cells(1, et_cc + 5).Value = "5% of (Final - Initial)"
        cells(2, et_cc + 5).Value = "=0.05*(%s-%s)" % (xladdress.cellStr(2, et_cc + 4),
                                                       xladdress.cellStr(2, et_cc + 3))
        cells.Columns(et_cc + 5).AutoFit()

        # 7.4.6 - highlight first measurement within 5% of final,
        # provided that no subsequent points are not within 5% of final
        row_pv95 = self._find_pv95(cells, cond_data, et_cc)

        t95_cell = xladdress.cellStr(row_pv95, et_cc - 1)
        lowest_addr = cells(first_data_row, et_cc - 1).Address

        # 7.4.7 - time from start of batch to t95
        cells(1, et_cc + 6).Value = "T95"
        cells(2, et_cc + 6).Value = "=(%s - %s)*24*60*60" % (t95_cell, lowest_addr)
        cells(2, et_cc + 6).NumberFormat = "0.0"
        self.t95 = cells(2, et_cc + 6).Value

        # Format chart axes scale
        ymin = math.floor(cells(2, et_cc + 3).Value2 * 0.9 * 10) / 10
        ymax = math.ceil(cells(2, et_cc + 4).Value2 * 1.1 * 10) / 10
        xlcom.FormatAxesScale(chart, None, None, ymin, ymax)

        return

    def _generate_et_formulas(self, row, col, endrow):
        formulas = []
        ref_cell = xladdress.cellStr(row, col, 1, 1)
        for r in range(row, endrow + 1):
            formula = "=(%s - %s)*24*60*60" % (xladdress.cellStr(r, col),
                                               ref_cell)

            # Excel demands data to be pasted as list tuples.
            # List of rows. Ie, list[row][column].
            formulas.append((formula,))
        return formulas


def __purge_xl():
    xl = xlcom.Excel(new=False)
    for wb in xl.Workbooks:
        wb.Close(False)
    xl.Quit()


def test_basic():
    __purge_xl()
    c = CompiledMixingTime()
    mt = c.add_csv("C:\\Users\\PBS Biotech\\Downloads 140827\\conductivity\\mt 1.2.csv")
    mt.cv = "phBRaw"
    c.analyze_all()


def test_open_from_batchname():
    __purge_xl()
    c = CompiledMixingTime()
    c.add_frombatchname("192.168.1.7", "mt 12rpm 1.1")
    c.analyze_all()


def M15_TR_005a_test():
    import re
    from hello import logger
    logger = logger.BuiltinLogger(__name__)

    path = "C:\\.replcache\\mixing_time_raw\\"
    mixing_test_re = re.compile(r"mt (\d{1,2})\s*rpm (\d+)\.(\d+)")
    si = CompiledMixingSaveAsInfo(path.replace("_raw", "_mixing"))
    c = CompiledMixingTime(saveas_info=si, logger=logger)
    for file in os.listdir(path):
        m = mixing_test_re.match(file)
        if not m:
            continue
        if m.groups()[1] == "5":
            c.add_csv(path + file)
    c.sort_tests(key=lambda t: int(mixing_test_re.match(t.name).groups()[0]))
    c.analyze_all()

if __name__ == '__main__':
    __purge_xl()
    M15_TR_005a_test()
