"""

Created by: Nathan Starkweather
Created on: 02/03/2016
Created in: PyCharm Community Edition


"""
from os import makedirs
from os.path import split as path_split
from re import match
from const import xlXYScatter, xlByRows, xlDown, xlToRight, xlOpenXMLWorkbook
from hello.hello import open_hello, TrueError, HelloError
from pbslib import pretty_date
from xllib.xladdress import cellStr, cellRangeStr
from xllib.xlcom import xlObjs, HiddenXl, AddTrendlines, CreateChart, FormatChart, CreateDataSeries

__author__ = 'Nathan Starkweather'


class _KLADataFile():
    """ Data file for kLA test data. In HELLO, this is the "Data Report"
     type of batch report.

     This class is responsible for downloading the report and saving it under
     "save_name".
    """
    def __init__(self, name=None, id=None, contents=None, save_name=None, ipv4=None):
        self.name = name
        self.id = id
        self.contents = contents
        self.filename = save_name
        self.print = print
        self.ipv4 = ipv4

    @classmethod
    def from_download(cls, batch_name, save_name, ipv4):
        """ Constructor from batch name, save_name, and ipv4 address """
        self = cls(batch_name, None, None, save_name, ipv4)
        self.download()
        return self

    def read(self):
        if not self.contents:
            self.download()
        return self.contents

    def download(self):
        max_tries = 20
        if self.ipv4 is None:
            raise ValueError("Require IPV4 to download batch")
        app = open_hello(self.ipv4)
        b = self._try_getreport(app, max_tries)
        if self.filename:
            with open(self.filename, 'wb') as f:
                f.write(b)
        self.contents = b

    def _try_getreport(self, app, max_tries=20):
        n = 1
        batch = None  # pycharm
        while True:
            app.login()
            self.print("\rAttempting to download report: Attempt #%d of %d              "
                       % (n, max_tries))
            try:
                batch = app.getdatareport_bybatchname(self.name)
            except TrueError:
                if n > max_tries:
                    raise
                try:
                    app.logout()
                except HelloError:
                    pass
                app.reconnect()
                n += 1
            else:
                break
        return batch


class _KLAMetaData():
    """ Metadata about a KLA report
    for storing context about the test,
    analysis, etc.
    """


class KLAReportFile():
    """ Class Responsible for performing individual KLA test analysis.
    Cohesive with KLAAnalyzer to compile data. """

    def __init__(self, raw_file, save_name, metadata):
        self.raw_file = raw_file
        self.save_name = save_name
        self.metadata = metadata or _KLAMetaData()

    @classmethod
    def from_data_file(cls, datafile):
        """
        @type datafile: kla.analyzer._KLADataFile
        """
        self = cls(datafile.filename, None, None)
        return self

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

    _m_rows = 6
    _m_cols = 2

    def __init__(self, wb, ws, cells, start_row, end_row, date_col):
        self.wb = wb
        self.ws = ws
        self.cells = cells
        self.start_row = start_row
        self.end_row = end_row
        self.date_col = date_col
        self.m_col_1 = date_col + 4
        self.m_col_2 = date_col + 5

    def m_addr(self, row, col, abs=True):
        """
        @rtype: str
        """
        cell = self.m_cells(row, col)
        if abs:
            return cell.Address
        else:
            return cell.GetAddress(False, False)

    def m_cells(self, row, col):
        return self.cells(row + self.start_row - 1, col + self.m_col_1 - 1)

    def close(self):
        """ Release references """
        self.wb = self.ws = self.cells = None

    def get_ranges(self):
        return self._make_named_ranges(self.wb, self.ws, self.date_col)

    def _add_data_table(self, date_col):

        m_addr = self.m_addr

        # cell formulas for "x_range" and "y_range" in docstring matrix
        x_range = '=%s&%s&":"&%s&%s' % (m_addr(1, 1), m_addr(2, 1),
                                        m_addr(1, 1), m_addr(3, 1))
        y_range = '=%s&%s&":"&%s&%s' % (m_addr(1, 2), m_addr(2, 1),
                                        m_addr(1, 2), m_addr(3, 1))

        # column letters
        x_col = cellStr(1, date_col + 1).replace("1", "")
        y_col = cellStr(1, date_col + 3).replace("1", "")

        # m and b
        linest_formula = "=index(linest(indirect(%s), indirect(%s)), %d)"
        addy_y = m_addr(4, 2)
        addy_x = m_addr(4, 1)
        m_form = linest_formula % (addy_y, addy_x, 1)
        b_form = linest_formula % (addy_y, addy_x, 2)
        top_left = self.m_cells(1, 1)
        bottom_right = self.m_cells(6, 2)

        self.cells.Range(top_left, bottom_right).Value = [
            [x_col, y_col],
            [self.start_row, None],
            [self.end_row, None],
            [x_range, y_range],
            ["m", "b"],
            [m_form, b_form]
        ]

        self.m_cells(1, 1).EntireColumn.NumberFormat = "General"

    def _make_named_ranges(self, wb, ws, date_col):

        self._add_data_table(date_col)

        # address range strings for first cell in x, f(x), and f(-ln(100-x)) columns
        x_col_start_cell = cellStr(self.start_row, date_col + 1, 1, 1)
        lin_col_start_cell = cellStr(self.start_row, date_col + 2, 1, 1)
        ln_col_start_cell = cellStr(self.start_row, date_col + 3, 1, 1)

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
        named_range_formula = "=offset(%s%%s,%s%s-%d,0):" \
                              "offset(%s%%s,%s%s-%d,0)"
        named_range_formula %= (sheet_name, sheet_name, self.m_addr(2, 1), self.start_row,
                                sheet_name, sheet_name, self.m_addr(3, 1), self.start_row)

        bob_formula_ln = named_range_formula % (x_col_start_cell, x_col_start_cell)
        fred_formula_ln = named_range_formula % (ln_col_start_cell, ln_col_start_cell)
        bob_formula_lin = bob_formula_ln
        fred_formula_lin = named_range_formula % (lin_col_start_cell, lin_col_start_cell)

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
    """
        @ivar _tests: [KLAReportFile]
        @type _tests: [KLAReportFile]
        """
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
        t = _KLADataFile(name, None, None, filename)
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
                f.analyze()
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



