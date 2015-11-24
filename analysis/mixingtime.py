"""

Created by: Nathan Starkweather
Created on: 11/19/2015
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'


from officelib.xllib import xlcom, xladdress
from officelib import const
import tempfile
from hello.hello import HelloApp
from hello.logger import BuiltinLogger

###################
# Utility Functions
###################


def _extract_cell_data(cells, top_left, bottom_right):
    alldata = cells.Range(top_left, bottom_right).Value
    return list(zip(*alldata))

def _ave(o):
    return sum(o) / len(o)

############
# Exceptions
############


class MixingTimeAnalysisException(Exception):
    pass

#########
# Classes
#########


class CompiledMixingTime():
    """
    Compiled collection of mixing time tests. Contains a list
     of tests, and adds data to a spreadsheet.

     Intended to be the primary entry point. Uses a BuiltinLogger
     passed on to all child tests created through its interface.
    """
    def __init__(self, xl=None, wb=None, logger=None):
        self.xl = xl
        self.wb = wb
        self.logger = logger or BuiltinLogger(self.__class__.__name__)
        self.tests = []

    def analyze_all(self):
        for mt in self.tests:
            mt.run_analysis()
            self.add_to_compiled(mt)

    def add_csv(self, csv):
        mt = self._create_test_from_csv(csv)
        self.add_test(mt)
        return mt

    def add_test(self, test):
        self.tests.append(test)

    def _create_test_from_csv(self, file):
        return MixingTimeTest.from_csv(file, self.logger)

    def from_csv_list(self, files):
        for file in files:
            self.add_csv(file)

    def add_to_compiled(self, mixing_test):
        raise NotImplementedError


class MixingTimeTest():
    """
    Represents an individual mixing time test. Opens raw batch file
    and performs analysis.

    Intended to be instantized by above CompiledMixingTime. Can
    be used directly for individual tests or customization.
    """
    def __init__(self, xl=None, wb=None, logger=None, conductivity_var="phARaw"):
        self.xl = xl
        self.wb = wb
        self.cv = conductivity_var
        self.logger = logger or BuiltinLogger(self.__class__.__name__)

    @classmethod
    def from_csv(cls, csv, logger=None):
        """
        @param csv: filename of csv file
        @param logger: Logger

        Instantize class from filename of raw batch file.
        Enter function at IP00043 Rev A 7.4.2
        """
        xl, wb = xlcom.xlBook2(csv)
        return cls(xl, wb, logger)

    @classmethod
    def from_batchname(cls, ipv4, batch_name, logger=None):
        """
        @param ipv4: IP address of bioreactor
        @param batch_name: batch name of test batch
        @param logger: Logger

        Enter function at IP00043 Rev A 7.4.1
        """
        app = HelloApp(ipv4)
        app.login()
        r = app.getdatareport_bybatchname(batch_name)
        t = tempfile.NamedTemporaryFile("wb", suffix=".csv")
        t.write(r)
        return cls.from_csv(t.name, logger)

    def _find_logger_ts_1k(self, cells):
        self.logger.debug("Searching for logger column: \"%s\"", self.cv)
        logger_col = cells.Find(What="LoggerMaxLogInterval(ms)",
                                After=cells(1, 1), SearchOrder=const.xlByRows)
        logger_col_values = cells.Columns(logger_col.Column + 1)
        first_1k = logger_col_values.Find(What="1000", SearchOrder=const.xlByColumns)
        logger_timestamp = cells(first_1k.Row, logger_col.Column).Value
        return logger_timestamp

    def _add_cond_et_col(self, cells, logger_timestamp):
        self.logger.debug("Creating elapsed time column.")
        cc = cells.Find(What=self.cv, After=cells(1, 1), SearchOrder=const.xlByRows)
        cc_col = cc.Column
        cc_end_row = cc.End(const.xlDown).Row
        cond_data = _extract_cell_data(cells, cc, cells(cc_end_row, cc_col + 1))
        ts_data = cond_data[0][1:]
        for row, data in enumerate(ts_data, 2):
            if data > logger_timestamp:
                break
        else:
            raise MixingTimeAnalysisException("Failed to find conductivity start timestamp.")
        et_formulas = self._generate_et_formulas(row, cc_col, len(ts_data) + 1)
        cells.Columns(cc_col + 1).Insert()
        et_col = cells.Columns(cc_col + 1)
        cells.Range(et_col.Cells(row, 1), et_col.Cells(cc_end_row, 1)).Value = et_formulas
        et_col.NumberFormat = "0.0"
        et_col.Cells(1, 1).Value = "Elapsed Time (sec)"
        return row, et_col, cc_end_row, cond_data

    def _add_raw_chart(self, cc_end_row, et_cc, first_data_row, ws):
        chart = xlcom.CreateChart(ws)
        xlcom.FormatChart(chart, None, "Time vs. Raw Voltage",
                          "Time (sec)", self.cv, False, False)
        x_rng, y_rng = xladdress.chart_range_strs(et_cc, et_cc + 1,
                                                  first_data_row, cc_end_row, ws.Name)
        xlcom.CreateDataSeries(chart, x_rng, y_rng)

    def _add_cond_ave_80s(self, cc_end_row, cells, cond_data, et_cc):
        ts_data = cond_data[0]
        end = len(ts_data) - 1
        last_pt = ts_data[-1]
        for i in range(end, -1, -1):
            if (last_pt - ts_data[i]).total_seconds() >= 80:
                i += 1  # back up
                break
        else:
            raise MixingTimeAnalysisException("Failed to find last 80 sec of data")
        first_pv_cell = (i + 1, et_cc + 1)
        last_pv_cell = (cc_end_row, et_cc + 1)
        ave_last_80 = "=average(%s:%s)" % (xladdress.cellStr(*first_pv_cell),
                                           xladdress.cellStr(*last_pv_cell))
        cells(1, et_cc + 4).Value = "Average last 80 sec"
        cells(2, et_cc + 4).Value = ave_last_80
        cells.Columns(et_cc + 4).AutoFit()

    def run_analysis(self):
        """
         XXX This analysis routine assumes data collected using the batch
             file method detailed in IP00043!
        """

        # Initialize
        self.logger.info("Beginning analysis on: %s", self.wb.Name)
        ws = self.wb.Worksheets(1)
        cells = ws.Cells

        # 7.4.3 - Find first logger max log interval timestamp
        logger_timestamp = self._find_logger_ts_1k(cells)

        # 7.4.3 - Elapsed Time column for conductivity
        first_data_row, et_col, cc_end_row, cond_data = self._add_cond_et_col(cells, logger_timestamp)
        et_cc = et_col.Column

        # 7.4.4 - Graph time vs conductivity pv
        self._add_raw_chart(cc_end_row, et_cc, first_data_row, ws)

        # 7.4.5 - Add initial conductivity, final ave conductivity over 80 sec
        free_col = cells.Columns(et_cc + 3)
        for _ in range(4):
            free_col.Insert()

        # 7.4.5.1 - Conductivity at t = 0 + header
        cells(1, et_cc + 3).Value = "Conductivity (T=0)"
        cells(2, et_cc + 3).Value = "=" + xladdress.cellStr(first_data_row,
                                                            et_cc + 1)
        cells.Columns(et_cc + 3).AutoFit()

        # 7.4.5.2 - final conductivity last 80 sec of batch
        self._add_cond_ave_80s(cc_end_row, cells, cond_data, et_cc)

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


if __name__ == '__main__':
    __purge_xl()

    c = CompiledMixingTime()
    mt = c.add_csv("C:\\Users\\PBS Biotech\\Downloads 140827\\conductivity\\mt 1.2.csv")
    mt.cv = "phBRaw"
    c.analyze_all()
