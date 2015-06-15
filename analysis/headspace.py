"""

Created by: Nathan Starkweather
Created on: 01/23/2015
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'


from officelib.xllib import xlcom, xladdress
from officelib import const
import os


debug = 1
if debug:
    dprint = print
else:
    dprint = lambda *_, **__: None


class HeadspaceError(Exception):
    pass


_data_path = "C:\\Users\\Public\\Documents\\PBSSS\\80L mech testing\\" \
             "Headspace gas PID tuning\\"


class HeadspaceDataAnalyzer():
    elapsed_time_header = "Elapsed Time (min)"

    def __init__(self, file_name=None, path=_data_path):
        self.path = path
        self.file_name = file_name

        self.xl = self.wb = self.ws = self.cells = None
        self.phdo_chart = None
        self.feedback_chart = None
        self.request_chart = None
        self.ninserts = 0

    @classmethod
    def from_download(cls, batch_name, ipv4, save_path=_data_path, save_name=None):
        from hello.hello import HelloApp
        app = HelloApp(ipv4)
        app.login()
        report = app.getdatareport_bybatchname(batch_name)
        save_name = save_name or os.path.join(save_path, batch_name + ".csv")
        with open(save_name, 'wb') as f:
            f.write(report)
        return cls(save_name)

    def main(self):

        self.xl, self.wb, self.ws, self.cells = xlcom.xlObjs(self.file_name)
        with xlcom.HiddenXl(self.xl):
            self._analyze(self.file_name)

    def set_axis_name(self, axis, name):
        axis.HasTitle = True
        axis.AxisTitle.Text = name

    def autofit_columns(self, ws):
        ws.UsedRange.EntireColumn.AutoFit()
        # i = 1
        # cols = ws.Columns
        # while True:
        #     c = cols(i)
        #     if not c.Cells(1, 1).Text:
        #         break
        #     c.AutoFit()
        #     i += 3

    def xl_save_name(self, file_name):
        # save_name = ''.join(file_name.split(".")[:-1])
        save_name, ext = os.path.splitext(file_name)
        save_name += ".xlsx"
        return save_name

    def format_axes(self, chart, xtitle, y1title, y2title=None):
        # axes (type, group) - type 1 = xaxis - type 2 = yaxis (?)
        # group = axisgroup
        axes = chart.Axes
        xaxis = axes(1, 1)
        y1axis = axes(2, 1)
        self.set_axis_name(xaxis, xtitle)
        self.set_axis_name(y1axis, y1title)

        if y2title is not None:
            y2axis = axes(2, 2)
            self.set_axis_name(y2axis, y2title)
        # xlcom.FormatAxesScale(chart, 0)

    def move_chart(self, chart, sheet_name):
        chart.Location(const.xlLocationAsNewSheet, sheet_name)

    def add_ph_do_chart(self, cells, ws):

        chart = xlcom.CreateChart(ws)

        chart_title = "Headspace Tuning pH & DO Data"
        x_axis_title = "Time"
        xlcom.FormatChart(chart, None, chart_title, x_axis_title)

        ph_name = "pHPV"
        do_name = "DOPV(%)"

        self.add_to_chart_from_header(chart, cells, ph_name)
        self.add_to_chart_from_header(chart, cells, do_name, 2)
        self.format_axes(chart, x_axis_title, ph_name, do_name)

        sheet_name = "pH DO data"
        self.move_chart(chart, sheet_name)
        return chart

    def _analyze(self, file_name, autosave=1):

        dprint("Analyzing file:", file_name)
        self.autofit_columns(self.ws)

        # this causes the class to end up calling cells.Find twice
        # to lookup the column for each series we're interested in,
        # once here and once in the respective add_xxx_chart method.
        # This exists because the add_xxx_chart methods were added
        # first, and it makes it easier to refactor to just lump
        # them here.

        headers = ["pHPV", "DOPV(%)", "pHCO2ActualRequest(%)", "DON2FlowActualRequest(%)"]
        headers.extend("MFC%sFlowFeedback(LPM)" % g for g in ("CO2", "O2", "N2", "Air"))
        refcell = self.find_ref_cell(self.cells)
        dprint("Adding time formula columns")
        for h in headers:
            self.add_time_formula_by_header(self.cells, refcell, h)
        dprint("Adding pH/DO chart")
        self.add_ph_do_chart(self.cells, self.ws)
        dprint("Adding gases chart")
        self.add_gases_chart(self.cells, self.ws)
        dprint("Adding Request chart")
        self.add_request_chart(self.cells, self.ws)

        if autosave:
            save_name = self.xl_save_name(file_name)
            dprint("Saving as", save_name)
            self.wb.SaveAs(save_name)
        else:
            dprint("File analyzed but not saved!")

    def find_ref_cell(self, cells):
        c = 1
        lowest = None
        while True:
            dateval = cells(2, c).Value2
            if not dateval:
                break
            if lowest is None or dateval < lowest:
                lowest = dateval
            c += 3
        return cells(2, c - 3)

    def create_time_formulas(self, refcol, refrow, startcol, startrow, endrow):
        # brevity
        refaddr = xladdress.cellStr(refrow, refcol, 0, 1)
        # list of 1-tuples
        formulas = [("=(%s-%s)*24*60" % (xladdress.cellStr(i, startcol), refaddr),)
                    for i in range(startrow, endrow + 1)]
        return formulas

    def add_gases_chart(self, cells, ws):

        chart = xlcom.CreateChart(ws)

        chart_title = "Headspace Tuning Gas Flow Feedback"
        x_axis_title = "Time"
        xlcom.FormatChart(chart, None, chart_title, x_axis_title)

        gas_names = ["MFC%sFlowFeedback(LPM)" % g for g in ("CO2", "O2", "N2", "Air")]

        for g in gas_names:
            self.add_to_chart_from_header(chart, cells, g)

        self.format_axes(chart, "Time", "Flow (LPM)")
        self.move_chart(chart, "Feedback")

        return chart

    def add_request_chart(self, cells, ws):

        chart = xlcom.CreateChart(ws)
        chart_title = "Headspace Tuning Gas Request"
        x_axis_title = "Time"
        xlcom.FormatChart(chart, None, chart_title, x_axis_title)

        self.add_to_chart_from_header(chart, cells, "pHCO2ActualRequest(%)")
        self.add_to_chart_from_header(chart, cells, "DON2FlowActualRequest(%)")

        self.format_axes(chart, "Time", "Gas Request (%)")
        self.move_chart(chart, "Gas Request")

    def add_time_formula_by_header(self, cells, refcell, header):

        cell = cells.Find(What=header, After=cells(1, 1), SearchOrder=const.xlByRows)
        tc = cell.Column + 1
        endrow = cell.End(const.xlDown).Row
        cells.Columns(tc).Insert(const.xlShiftToRight)
        formulas = self.create_time_formulas(refcell.Column, refcell.Row, tc - 1, 2, endrow)
        cells(1, tc).Value = self.elapsed_time_header
        cells.Columns(tc).NumberFormat = "0.0"
        cells.Range(cells(2, tc), cells(endrow, tc)).Value = formulas
        self.ninserts += 1

    def add_to_chart_from_header(self, chart, cells, header, axisgroup=1, markersize=2):
        """
        @param chart: chart. Pass "None" to create a new chart
        @param cells: cells
        @param header: string to search for
        @return:
        """
        x, y = self.chart_range_str_by_header(cells, header, True)
        series = xlcom.CreateDataSeries(chart, x, y, header)
        series.AxisGroup = axisgroup
        series.MarkerSize = markersize
        return series

    def chart_range_str_by_header(self, cells, header, use_elapsed_time=True):
        cell = cells.Find(What=header, After=cells(1, 1), SearchOrder=const.xlByRows)
        xcol = cell.Column
        ycol = xcol + 1

        if use_elapsed_time:
            xcol += 1
            ycol += 1

        top = cell.Row + 1
        bottom = cell.End(const.xlDown).Row
        return xladdress.chart_range_strs(xcol, ycol, top, bottom, cells.Worksheet.Name)


def test():
    file = "C:\\Users\\Public\\Documents\\PBSSS\\80L mech testing\\" \
           "Headspace gas PID tuning\\pbs 80 mag 1 headspacetest001 #2.csv"
    HeadspaceDataAnalyzer(file).main()
    # main(file)


def download_batches_150128(do_download=False):
    import os

    pth = "C:\\Users\\Public\\Documents\\PBSSS\\80L mech testing\\" \
          "Headspace gas PID tuning\\"

    app = batches = None

    if do_download:
        from hello.hello import HelloApp

        app = HelloApp('192.168.1.4')
        app.login()
        batches = app.getBatches()
    pths = []

    for i in range(1, 4):
        bname = "headspacetest00%d" % i
        fname = os.path.join(pth, "PBS 80 Mesoblast 1 %s.csv" % bname)
        pths.append(fname)
        if do_download:
            dprint("Downloading batch report:", bname)
            bid = batches.getbatchid(bname)
            contents = app.getdatareport_bybatchid(bid)
            with open(fname, 'wb') as f:
                f.write(contents)
    return pths


def killxl():
    import subprocess
    subprocess.call("tskill.exe excel")


def run_150128():

    files = download_batches_150128()
    killxl()
    for file in files:
        HeadspaceDataAnalyzer(file).main()
        print("Analyzed file:", file)


def run_150129():
    batch = "headspacetest004"
    killxl()
    print("Downloading file %s..." % batch, flush=True)
    # hda = HeadspaceDataAnalyzer.from_download(batch, "192.168.1.4")
    hda = HeadspaceDataAnalyzer(os.path.join(_data_path, batch + ".csv"))
    print("Beginning Analysis...", flush=True)
    hda.main()


def run_150202():
    batches = ["headspacetest00%d" % i for i in range(1, 6)]
    killxl()
    for batch in batches:
        print("Downloading file %s..." % batch, flush=True)
        hda = HeadspaceDataAnalyzer.from_download(batch, "192.168.1.4")
        print("Beginning Analysis...", flush=True)
        hda.main()

if __name__ == '__main__':
    from datetime import datetime
    import sys
    ds = datetime.now().strftime("%y%m%d")
    func_name = "run_" + ds
    mod = sys.modules["__main__"]
    getattr(mod, func_name)()
